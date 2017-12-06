############
# Standard #
############
import math
import logging

###############
# Third Party #
###############
import numpy as np
from lmfit.models           import LorentzianModel
from bluesky.preprocessors  import run_wrapper
from ophyd.sim              import SynSignal, SynAxis

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.component import Component

##########
# Module #
##########
from hxrsnd import maximize_lorentz, rocking_curve
from hxrsnd.plans import euclidean_distance, calibration_scan, centroid_scan

logger = logging.getLogger(__name__)


class Diode(SynSignal):
    """
    Simulated Diode

    Evaluate a point on a Lorentz function based on the value of a motor

    By default, the amplitude and sigma values will create a max signal of 1.0,
    representing a normalized diode signal

    Parameters
    ----------
    name : str

    motor : obj

    motor_field : str
        Name of field to use as independent variable

    center : float
        Center position of Lorentz

    sigma : float, optional
        Width of distribution

    amplitude : float, optional
        Height of distribution

    noise_multiplier : float, optional
        Multipler for uniform noise of the diode. If left as None, no noise will
        be applied
    """
    def __init__(self, name, motor, motor_field, center,
                 sigma=1, amplitude=math.pi,
                 noise_multiplier=None, **kwargs):
        # Eliminate noise if not requested
        noise = noise_multiplier or 0.
        lorentz = LorentzianModel()

        def func():
            # Evaluate position in distribution
            m = motor.read()[motor_field]['value']
            v = lorentz.eval(x=np.array(m), amplitude=amplitude, sigma=sigma,
                             center=center)
            # Add uniform noise
            v += np.random.uniform(-1, 1) * noise
            return v

        # Instantiate Reader
        super().__init__(name=name, func=func, **kwargs)


class SynCentroid(SynSignal):
    """
    Synthetic centroid signal.
    """
    def __init__(self, motors, weights, motor_field=None, noise_multiplier=None, 
                 name=None, *args, **kwargs):
        # Eliminate noise if not requested
        noise = noise_multiplier or 0.
        
        
        def func():
            # Evaluate the positions of each motor
            pos = [m.read()[motor_field or m.name]['value'] for m in motors]
            # Get the centroid position
            cent = np.dot(pos, weights)
            # Add uniform noise
            cent += int(np.round(np.random.uniform(-1, 1) * noise))
            return cent
        
        # Instantiate the synsignal
        super().__init__(name=name, func=func, **kwargs)
            

class SynCamera(Device):
    """
    Simulated camera that has centroids as components. 
    """
    def __init__(self, motor1, motor2, delay, name=None, *args, **kwargs):
        # Create the base class
        super().__init__("SYN:CAMERA", name=name, *args, **kwargs)
        
        # Define the centroid components using the inputted motors
        self.centroid_x = SynCentroid(name="_".join([self.name, "centroid_x"]), 
                                      motors=[motor1, delay], weights=[1,.25])
        self.centroid_y = SynCentroid(name="_".join([self.name, "centroid_y"]), 
                                      motors=[motor2, delay], weights=[1,-.25])
        
        # Add them to _signals
        self._signals['centroid_x'] = self.centroid_x
        self._signals['centroid_y'] = self.centroid_y

        # Add them to the read_attrs
        self.read_attrs = ["centroid_x", "centroid_y"]

    def trigger(self):
        return self.centroid_x.trigger() & self.centroid_y.trigger()
    
# Simulated Crystal motor that goes where you tell it
crystal = SynAxis(name='angle')
m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_lorentz_maximize(fresh_RE):
    # Simulated diode readout
    diode = Diode('intensity', crystal, 'angle', 10.0, noise_multiplier=None)
    # Create plan to maximize the signal
    plan  = run_wrapper(maximize_lorentz(diode, crystal, 'intensity',
                                         step_size=0.2, bounds=(9., 11.),
                                         position_field='angle',
                                         initial_guess = {'center' : 8.}))
    # Run the plan
    fresh_RE(plan)

    # Trigger an update
    diode.trigger()
    #Check that we were within 10%
    assert np.isclose(diode.read()['intensity']['value'], 1.0, 0.1)


def test_rocking_curve(fresh_RE):
    # Simulated diode readout
    diode = Diode('intensity', crystal, 'angle', 10.0, noise_multiplier=None)
    # Create plan to maximize the signalplan
    plan  = run_wrapper(rocking_curve(diode, crystal, 'intensity',
                                      coarse_step=0.1, fine_step=0.05,
                                      bounds=(5., 15.), fine_space=2.5,
                                      position_field='angle',
                                      initial_guess = {'center' : 8.}))
    # Run the plan
    fresh_RE(plan)

    # Trigger an update
    diode.trigger()
    # Check that we were within 10%
    assert np.isclose(diode.read()['intensity']['value'], 1.0, 0.1)

def test_euclidean_distance(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")    
    # Define the distance plan that makes the assertion
    def test_plan():
        distance = yield from euclidean_distance(
            camera, ['centroid_x', 'centroid_y'], [1,1])
        assert np.isclose(distance, math.sqrt(2))
    
    # Wrap the plan
    plan = run_wrapper(test_plan())
    # And now run it
    fresh_RE(plan)

def test_1_signal_calibration_scan(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        df = yield from calibration_scan(camera, ['centroid_x'], 
                                         delay, [m1], -5, 5, 11,)    
    # Wrap the plan
    plan = run_wrapper(test_plan())
    # And now run it
    fresh_RE(plan)    

def test_centroid_scan(fresh_RE):
    # Simulated camera
    camera = SynCamera(m1, m2, delay, name="camera")
    # Create the plan
    def test_plan():
        delay_scan = (yield from centroid_scan(camera, delay, -5, 5, 11))
        assert True not in delay_scan.isnull().values

    plan = run_wrapper(test_plan())
    # Run the plan
    fresh_RE(plan)

