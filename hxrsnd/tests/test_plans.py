############
# Standard #
############
import math
import logging

###############
# Third Party #
###############
import numpy as np
from lmfit.models      import LorentzianModel
from bluesky.plans     import run_wrapper
from bluesky.examples  import Mover, Reader

##########
# Module #
##########
from hxrsnd import maximize_lorentz
from hxrsnd.utils import get_logger

logger = get_logger(__name__, log_file=False)


class Diode(Reader):
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
        #Eliminate noise if not requested
        noise = noise_multiplier or 0.
        lorentz = LorentzianModel()

        def func():
            #Evaluate position in distribution
            m = motor.read()[motor_field]['value']
            v = lorentz.eval(x=m, amplitude=amplitude, sigma=sigma,
                             center=center)
            #Add uniform noise
            v += np.random.uniform(-1, 1) * noise
            return v

        #Instantiate Reader
        super().__init__(name, {name : func}, **kwargs)

#Simulated Crystal motor that goes where you tell it
crystal = Mover('angle', {'angle' : lambda x : x}, {'x' :0})

def test_lorentz_maximize(fresh_RE):
    #Simulated diode readout
    diode = Diode('intensity', crystal, 'angle', 10.0, noise_multiplier=None)
    #Create plan to maximize the signal
    plan  = run_wrapper(maximize_lorentz(diode, crystal, 'intensity',
                                         nsteps=100, bounds=(9., 11.),
                                         position_field='angle',
                                         initial_guess = {'center' : 8.}))
    #Run the plan
    fresh_RE(plan)

    #Check that we were within 10%
    assert np.isclose(diode.read()['intensity']['value'], 1.0, 0.1)




