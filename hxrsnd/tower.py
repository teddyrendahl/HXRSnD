############
# Standard #
############
import logging

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
from pcdsdevices.component import Component, FormattedComponent

##########
# Module #
##########
from .utils import flatten
from .bragg import bragg_angle, bragg_energy
from .state import OphydMachine
from .rtd import OmegaRTD
from .aerotech import AeroBase, RotationAero, LinearAero
from .attocube import EccBase, TranslationEcc, GoniometerEcc, DiodeEcc
from .diode import (HamamatsuDiode, HamamatsuXMotionDiode,
                                     HamamatsuXYMotionCamDiode)

logger = logging.getLogger(__name__)

class TowerBase(Device):
    """
    Base tower class.
    """
    def __init__(self, prefix, desc=None, pos_inserted=None, pos_removed=None,
                 *args, **kwargs):
        self.desc = desc
        self.pos_inserted = pos_inserted
        self.pos_removed = pos_removed
        super().__init__(prefix, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name
        
    def set_energy(self, E, *args, **kwargs):
        """
        Placeholder for the energy setter. Implement for each TowerBase
        subclass.
        """
        pass

    @property
    def energy(self):
        """
        Returns the energy of the tower according to the angle of the
        arm.

        Returns
        -------
        E : float
            Energy of the delay line.
        """
        return bragg_energy(self.theta)

    @energy.setter
    def energy(self, E):
        """
        Sets the theta of the tower to the desired energy. Alias for 
        set_energy(E).

        Parameters
        ----------
        E : float
            Desired energy to set the tower to.
        """
        status = self.set_energy(E)
    
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

    def check_status(self, energy=True, delay=False):
        """
        Checks to make sure that all the energy motors are not in a bad state. 
        Will include the delay motor if the delay argument is True.

        Parameters
        ----------
        energy : bool, optional
            Check the energy motors.

        delay : bool, optional
            Check the delay motor.
        """
        # Create the list of motors we will iterate through
        motors = []
        if energy:
            motors += self._energy_motors
        if delay:
            motors += [self.L]
        
        # Check that we can move all the motors
        for motor in motors:
            try:
                motor.check_status()
            except Exception as e:
                err = "Motor {0} got an exception: {1}".format(motor.name, e)
                logger.error(err)
                raise e    

    def stop(self):
        """
        Stops the motions of all the motors.
        """
        self._apply_all("stop", (AeroBase, EccBase))
    
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

        if print_status:
            print(status)
        else:
            return status

    def __repr__(self):
        """
        Returns the status of the device. Alias for status().

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
        self._energy_motors = [self.tth, self.th1, self.th2]

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

    def set_energy(self, E, wait=False, check_status=True):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for each motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Check to make sure the motors are in a valid state to move
        if check_status:
            self.check_status()
        logger.debug("\nMoving {tth} to {tth_theta} \nMoving {th1} and {th2} to"
                     " {th_theta}.".format(tth=self.tth.name, th1=self.th1.name, 
                                           th2=self.th2.name, tth_theta=2*theta,
                                           th_theta=theta))

        # Convert to theta1
        theta = bragg_angle(E=E)

        # Do the move
        move_pos = [2*theta, theta, theta]
        status = [motor.move(pos, wait=False, check_status=False) for
                  move, pos in zip(motors, move_pos)]

        # Wait for the motions to finish
        if wait:
            for s in status:
                logger.info("Waiting for {} to finish move ...".format(
                    s.device.name))
                status_wait(s)
                
        return status

    def set_length(self, position, wait=False, *args, **kwargs):
        """
        Sets the position of the linear delay stage in mm.

        Parameters
        ----------
        position : float
            Position to move the delay motor to.

        wait : bool, optional
            Wait for motion to complete before returning the console.

        Returns
        -------
        status : MoveStatus
            Status object of the move.
        """
        return self.L.move(position, wait=wait, *args, **kwargs)

    @property
    def length(self):
        """
        Returns the position of the linear delay stage (L) in mm.

        Returns
        -------
        position : float
            Position in mm of the linear delay stage.
        """
        return self.L.position

    @length.setter
    def length(self, position):
        """
        Sets the position of the linear delay stage in mm.

        Parameters
        ----------
        position : float
            Position to move the delay motor to.
        """
        status = self.set_length(position, wait=False)

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

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self._energy_motors = [self.th]

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

    def set_energy(self, E, wait=False, check_status=True):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for motion to complete before returning the console.

        check_status : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Check to make sure the motors are in a valid state to move
        if check_status:
            self.check_status()
        logger.debug("\nMoving {th} to {theta}".format(
            th=self.th.name, theta=theta))
            
        # Convert to theta
        theta = bragg_angle(E=E)

        status = self.th.move(theta, wait=wait)
        return status

