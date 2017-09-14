"""
Script to hold the split and delay devices.
"""
############
# Standard #
############
import logging
from enum import Enum

###############
# Third Party #
###############
import numpy as np
from ophyd.utils.epics_pvs import raise_if_disconnected
from ophyd.status import wait as status_wait

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.component import (Component, FormattedComponent)

##########
# Module #
##########
from .bragg import (bragg_angle, bragg_energy)
from .state import OphydMachine
from .rtd import OmegaRTD
from .aerotech import (AeroBase, RotationAero, LinearAero)
from .attocube import (EccBase, TranslationEcc, GoniometerEcc, 
                                        DiodeEcc)
from .diode import (HamamatsuDiode, HamamatsuXMotionDiode,
                                     HamamatsuXYMotionCamDiode)

logger = logging.getLogger(__name__)


class TowerBase(Device):
    """
    Base tower class.
    """
    def __init__(self, prefix, desc=None, pos_inserted=None, pos_removed=None,
                 *args, **kwargs):
        self.pos_inserted = pos_inserted
        self.pos_removed = pos_removed
        self.desc=desc
        super().__init__(prefix, *args, **kwargs)
        if desc is None:
            self.desc = self.name
        
    def E_to_theta(self, E, ID="Si", hkl=(2,2,0)):
        """
        Computes theta1 based on the inputted energy. This should function
        as a lookup table.
        
        Parmeters
        ---------
        E : float
            Energy to convert to theta1

        ID : str, optional
            Chemical fomula : 'Si'

        hkl : tuple, optional
            The reflection : (2,2,0)

        Returns
        -------
        theta1 : float
            Expected bragg angle for E
        """
        self.E = E
        return bragg_angle(E=E, ID=ID, hkl=hkl)

    @property
    def energy(self):
        """
        Sets angle of the tower according to the inputted energy.

        Returns
        -------
        E : float
            Energy of the delay line.
        """
        return bragg_energy(self.theta)

    @energy.setter
    def energy(self, E):
        """
        Placeholder for the energy setter. Implement for each TowerBase
        subclass.
        """
        pass
    
    @property
    def position(self):
        """
        Current position of the tower. Implment this for each TowerBase
        subclass.
        """
        return None

    @property
    def theta(self):
        """
        Bragg angle the tower is currently set to maximize.

        Returns
        -------
        position : float
            Current position of the tower.
        """
        return self.position

    def insert(self, *args, **kwargs):
        """
        Moves the tower x motor to `self.pos_inserted`.

        Returns
        -------
        status : MoveStatus
            Status of the move.

        Raises
        ------
        ValueError
            If pos_inserted is set to None and insert() is called.
        """
        if self.pos_inserted is None:
            raise ValueError("Must set pos_inserted to use insert method.")
        return self.x.move(self.pos_inserted, *args, **kwargs)

    def remove(self, *args, **kwargs):
        """
        Moves the tower x motor to `self.pos_removed`.

        Returns
        -------
        status : MoveStatus
            Status of the move.

        Raises
        ------
        ValueError
            If pos_removed is set to None and remove() is called.
        """
        if self.pos_removed is None:
            raise ValueError("Must set pos_removed to use remove method.")        
        return self.x.move(self.pos_removed, *args, **kwargs)

    @property
    def inserted(self):
        """
        Returns whether the tower is in the inserted position (or close to it).

        Returns
        -------
        inserted : bool
            Whether the tower is inserted or not.

        Raises
        ------
        ValueError
            If pos_inserted is set to None and inserted is called.        
        """
        if self.pos_inserted is None:
            raise ValueError("Must set pos_inserted to check if inserted.")
        return np.isclose(self.pos_inserted, self.position, atol=0.1)

    def _apply_all(self, method, subclass=object, method_args=None,
                   method_kwargs=None):
        """
        Runs the method for all devices that are of the inputted subclass. All
        additional arguments and key word arguments are passed as inputs to the
        method.

        Parameters
        ----------
        method : str
            Method of each device to run.

        subclass : class
            Subclass to run the methods for.

        method_args : tuple, optional
            Positional arguments to pass to the method

        method_kwargs : dict, optional
            Key word arguments to pass to the method
        """
        # Replace method_args and method_kwargs with an empty tuple and dict
        if method_args is None:
            method_args = ()
        if method_kwargs is None:
            method_kwargs = {}

        ret = []
        # Check if each signal is a subclass of subclass then run the method
        for sig_name in self.signal_names:
            signal = getattr(self, sig_name)
            if issubclass(type(signal), subclass):
                ret.append(getattr(signal, method)(*method_args,
                                                   **method_kwargs))
        return ret            
    
    def enable(self):
        """
        Enables all the aerotech motors.
        """
        self._apply_all("enable", (AeroBase, EccBase))

    def disable(self):
        """
        Disables all the aerotech motors.
        """
        self._apply_all("disable", (AeroBase, EccBase))

    def clear(self):
        """
        Disables all the aerotech motors.
        """
        self._apply_all("clear", AeroBase)

    def status(self, status="", offset=0, print_status=True, newline=False):
        """
        Returns the status of the tower.
        
        Parameters
        ----------
        status : str, optional
            The string to append the status to.
            
        offset : int, optional
            Amount to offset each line of the status.

        print_status : bool, optional
            Determines whether the string is printed or returned.

        newline : bool, optional
            Adds a new line to the end of the string.

        Returns
        -------
        status : str
            Status string.
        """
        status += "{0}{1}:\n{2}{3}\n".format(" "*offset, self.desc,
                                             " "*offset, "-"*(len(self.desc)+1))
        status_list = self._apply_all("status", (AeroBase, EccBase),
                                      method_kwargs={"offset":offset+2,
                                                     "print_status":False})
        status += "".join(status_list)
        if newline:
            status += "\n"

        if print_status is True:
            print(status)
        else:
            return status

    def __repr__(self):
        """
        Returns the status of the tower. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)

        
class DelayTower(TowerBase):
    """
    Delay Tower
    
    Components
    ----------
    tth : RotationAero
        Rotation axis of the entire delay arm

    th1 : RotationAero
        Rotation axis of the static crystal

    th2 : RotationAero
        Rotation axis of the delay crystal

    x : LinearAero
        Linear stage for insertion/bypass of the tower

    L : LinearAero
        Linear stage for the delay crystal

    y1 : TranslationEcc
        Y translation for the static crystal

    y2 : TranslationEcc
        Y translation for the delay crystal

    chi1 : GoniometerEcc
        Goniometer on static crystal

    chi2 : GoniometerEcc
        Goniometer on delay crystal

    dh : DiodeEcc
        Diode insertion motor

    diode : HamamatsuDiode
        Diode between the static and delay crystals

    temp : OmegaRTD
        RTD temperature sensor for the nitrogen.    
    """
    # Rotation stages
    tth = Component(RotationAero, ":TTH", desc="Two Theta")
    th1 = Component(RotationAero, ":TH1", desc="Theta 1")
    th2 = Component(RotationAero, ":TH2", desc="Theta 2")

    # Linear stages
    x = Component(LinearAero, ":X", desc="Tower X")
    L = Component(LinearAero, ":L", desc="Delay Stage")

    # Y Crystal motion
    y1 = FormattedComponent(TranslationEcc, "{self._prefix}:ECC:{self._y1}",
                            desc="Crystal 1 Y")
    y2 = FormattedComponent(TranslationEcc, "{self._prefix}:ECC:{self._y2}",
                            desc="Crystal 2 Y")

    # Chi motion
    chi1 = FormattedComponent(GoniometerEcc, "{self._prefix}:ECC:{self._chi1}",
                              desc="Crystal 1 Chi")
    chi2 = FormattedComponent(GoniometerEcc, "{self._prefix}:ECC:{self._chi2}",
                              desc="Crystal 2 Chi")

    # Diode motion
    dh = FormattedComponent(DiodeEcc, "{self._prefix}:ECC:{self._dh}",
                            desc="Diode Motor")

    # # Diode
    # diode = Component(HamamatsuDiode, ":DIODE", desc="Tower Diode")

    # # Temperature monitor
    # temp = Component(OmegaRTD, ":TEMP", desc="Tower RTD")

    def __init__(self, prefix, y1=None, y2=None, chi1=None, chi2=None, dh=None,
                 *args, **kwargs):
        self._y1 = y1 or "Y1"
        self._y2 = y2 or "Y2"
        self._chi1 = chi1 or "CHI1"
        self._chi2 = chi2 or "CHI2"
        self._dh = dh or "DH"
        self._prefix = prefix[:-3]
        super().__init__(prefix, *args, **kwargs)

    @property
    def position(self):
        """
        Returns the theta position of the arm (tth) in degrees.

        Returns
        -------
        position : float
            Position of the arm in degrees.
        """
        return self.tth.position

    @TowerBase.energy.setter
    def energy(self, E):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        # Convert to theta1
        # TODO: Error handling here
        theta = self.E_to_theta(E)

        logger.debug("\nMoving {tth} to {theta} \nMoving {th1} and {th2} to "
                     "{half_theta}.".format(
                         tth=self.tth.name, th1=self.th1.name,
                         th2=self.th2.name, theta=theta, half_theta=theta/2))

        motors = [self.tth, self.th1, self.th2]
        move_pos = [theta, theta/2, theta/2]

        # Check that we can move all the motors
        for motor in motors:
            try:
                motor.check_status()
            except Exception as e:
                err = "Motor {0} got an exception: {1}".format(motor.name, e)
                logger.error(err)
                raise e

        status = [motor.move(pos) for move, pos in zip(motors, move_pos)]

    @property
    def delay(self):
        """
        Returns the position of the linear delay stage (L) in mm.

        Returns
        -------
        position : float
            Position in mm of the linear delay stage.
        """
        return self.L.position

    @delay.setter
    def delay(self, position):
        """
        Sets the position of the linear delay stage in mm.

        Parameters
        ----------
        position : float
            Position to move the delay motor to.
        """
        self.L.move(position, wait=False)
        

class ChannelCutTower(TowerBase):
    """
    Channel Cut tower.

    Components
    ----------
    th : RotationAero
        Rotation stage of the channel cut crystal

    x : LinearAero
        Translation stage of the tower
    """
    # Rotation
    th = Component(RotationAero, ":TH", desc="Theta")

    # Translation
    x = Component(LinearAero, ":X", desc="Tower X")

    @property
    def position(self):
        """
        Returns the theta position of the crystal (th) in degrees.

        Returns
        -------
        position : float
            Position of the arm in degrees.
        """
        return self.th.position

    @property
    def theta(self):
        """
        Bragg angle the tower is currently set to maximize.

        Returns
        -------
        position : float
            Current position of the tower.
        """
        return 2*self.position    

    @TowerBase.energy.setter
    def energy(self, E):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        # Convert to theta
        # TODO: Error handling here
        theta = self.E_to_theta(E)

        logger.debug("\nMoving {th} to {theta}".format(th=self.th.name,
                                                       theta=theta))

        # Set the position of the motors on tower 2
        status_th = self.th.move(theta/2, wait=False)

        
class SplitAndDelay(Device):
    """
    Hard X-Ray Split and Delay System.

    Components
    ----------
    t1 : DelayTower
        Tower 1 in the split and delay system

    t4 : DelayTower
        Tower 4 in the split and delay system

    t2 : ChannelCutTower
        Tower 2 in the split and delay system

    t3 : ChannelCutTower
        Tower 3 in the split and delay system

    di : HamamatsuXYMotionCamDiode
        Input diode for the system
    
    dd : HamamatsuXYMotionCamDiode
        Diode between the two delay towers

    do : HamamatsuXYMotionCamDiode
        Output diode for the system

    dci : HamamatsuXMotionDiode
        Input diode for the channel cut line
    
    dcc : HamamatsuXMotionDiode
        Diode between the two channel cut towers
    
    dco : HamamatsuXMotionDiode
        Input diode for the channel cut line
    """
    # Delay Towers
    t1 = Component(DelayTower, ":T1", y1="A:ACT0", y2="A:ACT1",
                   chi1="A:ACT2", chi2="B:ACT0", dh="B:ACT1",
                   pos_inserted=21.1, pos_removed=0, desc="Tower 1")
    t4 = Component(DelayTower, ":T4", y1="C:ACT0", y2="C:ACT1",
                   chi1="C:ACT2", chi2="D:ACT0", dh="D:ACT1",
                   pos_inserted=21.1, pos_removed=0, desc="Tower 4")

    # Channel Cut Towers
    t2 = Component(ChannelCutTower, ":T2", pos_inserted=None, 
                   pos_removed=0, desc="Tower 2")
    t3 = Component(ChannelCutTower, ":T3", pos_inserted=None, 
                   pos_removed=0, desc="Tower 3")

    # SnD and Delay line diodes
    di = Component(HamamatsuXYMotionCamDiode, ":DIA:DI")
    dd = Component(HamamatsuXYMotionCamDiode, ":DIA:DD")
    do = Component(HamamatsuXYMotionCamDiode, ":DIA:DO")

    # Channel Cut Diodes
    dci = Component(HamamatsuXMotionDiode, ":DIA:DCI")
    dcc = Component(HamamatsuXMotionDiode, ":DIA:DCC")
    dco = Component(HamamatsuXMotionDiode, ":DIA:DCO")
    
    # Constants
    c = 299792458               # m/s
    gap = 0.055                 # m
    min_dist = 0.105            # m

    # TEMP
    t = 0

    def t_to_length(self, t, **kwargs):
        """
        Converts the inputted delay to the lengths on the delay arm linear
        stages.

        Parameters
        ----------
        t : float
            The desired delay from the system in picoseconds

        Returns
        -------
        length : float
            The distance between the delay crystal and the splitting or
            recombining crystal.
        """
        # Lets internally keep track of this
        self.t = t * 1e-12      # Convert to seconds

        # TODO : Double check that this is correct
        length = ((self.t*self.c + 2*self.gap * (1 - np.cos(
            2*self.t1.theta))/np.sin(self.t1.theta))/
                  (2*(1 - np.cos(2*self.t3.theta))))

        return length * 1000    # Convert to mm

    @property
    def energy(self):
        """
        Returns the energy the whole system is currently set to in eV

        Returns
        -------
        E1, E2 : tuple
            Energy for the delay line and channel cut line.
        """
        return self.t1.energy, self.t2.energy

    @energy.setter
    def energy(self, E):
        """
        Sets the energy for both the delay line and the channe cut line of the
        system.

        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        self.t1.energy = E
        self.t2.energy = E
        self.t3.energy = E
        self.t4.energy = E

    @property
    def energy1(self):
        """
        Returns the calculated energy based on the angle of the delay line

        Returns
        -------
        E1 : float
            Energy of the delay line.
        """
        return self.t1.energy

    @energy1.setter
    def energy1(self, E):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        self.t1.energy = E
        self.t4.energy = E
        
    @property
    def energy2(self):
        """
        Returns the calculated energy based on the angle of the channel cut
        line.

        Returns
        -------
        E : float
            Energy of the channel cut line.
        """
        return self.t2.energy

    @energy2.setter
    def energy2(self, E):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        self.t2.energy = E
        self.t3.energy = E
        
    @property
    def delay(self):
        """
        Returns the current expected delay of the system.

        Returns
        -------
        t : float
            Expected delay in picoseconds
        """
        # TODO: Replace with delay calculation.
        return self.t
        
    @delay.setter 
    def delay(self, t):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions.
        
        Parameters
        ----------
        t : float
            The desired delay from the system.
        """
        self.length = self.t_to_length(t)

        logger.debug("Input delay: {0}. \nMoving t1.L and t2.L to {1}".format(
            t, self.length))

        status_t1_L = self.t1.L.move(self.length, wait=False)
        status_t4_L = self.t4.L.move(self.length, wait=False)

        # # Wait for the status objects to register the moves as complete
        # if wait:
        #     logger.info("Waiting for {} to finish move ...".format(self.name))
        #     # TODO: Wait on the composite status
        #     # status_wait(status_composite)
        
        # TODO: Find a way to create composite statuses
        # return status_composite

    def status(self):
        """
        Returns the status of the split and delay system.
        
        Returns
        -------
        status : str            
        """
        status =  "Split and Delay System Status\n"
        status += "-----------------------------\n"
        status += "  Energy 1: {0}\n".format(np.round(self.energy1))
        status += "  Energy 2: {0}\n".format(np.round(self.energy2))
        status += "  Delay: {0}\n\n".format(self.delay)
        status = self.t1.status(status, 0, print_status=False, newline=True)
        status = self.t2.status(status, 0, print_status=False, newline=True)
        status = self.t3.status(status, 0, print_status=False, newline=True)
        status = self.t4.status(status, 0, print_status=False, newline=False)
        print(status)

    def __repr__(self):
        """
        Returns the status of the system. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)
