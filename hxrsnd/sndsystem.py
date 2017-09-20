"""
Script to hold the split and delay devices.

All units of time are in picoseconds, units of length are in mm.
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
from .utils import flatten
from .bragg import (bragg_angle, bragg_energy, cosd, sind)
from .state import OphydMachine
from .rtd import OmegaRTD
from .aerotech import (AeroBase, RotationAero, LinearAero)
from .attocube import (EccBase, TranslationEcc, GoniometerEcc, 
                                        DiodeEcc)
from .diode import (HamamatsuDiode, HamamatsuXMotionDiode,
                                     HamamatsuXYMotionCamDiode)
from .pneumatic import (ProportionalValve, PressureSwitch)

logger = logging.getLogger(__name__)

class SndDevice(Device):
    """
    Base Split and Delay device class.
    """

    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc=desc
        super().__init__(prefix, *args, **kwargs)
        if desc is None:
            self.desc = self.name

    def status(self, *args, **kwargs):
        """
        Status of the device. To be filled in by subclasses.
        """
        pass

    def __repr__(self):
        """
        Returns the status of the device. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)
            
    
class TowerBase(SndDevice):
    """
    Base tower class.
    """
    def __init__(self, prefix, pos_inserted=None, pos_removed=None,
                 *args, **kwargs):
        self.pos_inserted = pos_inserted
        self.pos_removed = pos_removed
        super().__init__(prefix, *args, **kwargs)
        
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

    def check_motors(self, energy=True, delay=False):
        """
        Checks to make sure that all the energy motors are not in a bad state. Will
        include the delay motor if the delay argument is True.

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

        if print_status is True:
            print(status)
        else:
            return status

        
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

    def set_energy(self, E, wait=False, check_motors=True):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for each motor to complete the motion.

        check_motors : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Check to make sure the motors are in a valid state to move
        if check_motors:
            self.check_motors()
        logger.debug("\nMoving {tth} to {theta} \nMoving {th1} and {th2} to "
                     "{half_theta}.".format(
                         tth=self.tth.name, th1=self.th1.name,
                         th2=self.th2.name, theta=theta, half_theta=theta/2))            

        # Convert to theta1
        theta = bragg_angle(E=E)

        # Do the move
        move_pos = [theta, theta/2, theta/2]            
        status = [motor.move(pos, wait=False, check_status=False) for
                  move, pos in zip(motors, move_pos)]

        # Wait for the motions to finish
        if wait:
            for s in status:
                logger.info("Waiting for {} to finish move ...".format(s.device.name))
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

    def set_energy(self, E, wait=False, check_motors=True):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for motion to complete before returning the console.

        check_motors : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Check to make sure the motors are in a valid state to move
        if check_motors:
            self.check_motors()
        logger.debug("\nMoving {th} to {theta}".format(
            th=self.th.name, theta=theta))
            
        # Convert to theta
        theta = bragg_angle(E=E)

        status = self.th.move(theta/2, wait=wait)
        return status


class SndVacuum(SndDevice):
    """
    Class that contains the various pneumatic components of the system.

    Components
    ----------
    t1_valve : ProportionalValve
        Proportional valve on T1.

    t4_valve : ProportionalValve
        Proportional valve on T4.

    vac_valve : ProportionalValve
        Proportional valve on the overall system.

    t1_pressure : PressureSwitch
        Pressure switch on T1.

    t4_pressure : PressureSwitch
        Pressure switch on T4.

    vac_pressure : PressureSwitch
        Pressure switch on the overall system.
    """
    t1_valve = Component(ProportionalValve, ":N2:T1")
    t4_valve = Component(ProportionalValve, ":N2:T4")
    vac_valve = Component(ProportionalValve, ":VAC")

    t1_pressure = Component(PressureSwitch, ":N2:T1")
    t4_pressure = Component(PressureSwitch, ":N2:T4")
    vac_pressure = Component(PressureSwitch, ":VAC")

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self._valves = [self.t1_valve, self.t4_valve, self.vac_valve]
        self._pressure_switch = [self.t1_pressure, self.t4_pressure,
                                self.vac_pressure]

    def status(self, status="", offset=0, print_status=True, newline=False):
        """
        Returns the status of the vacuum system.

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
        status += "{0}Vacuum\n{1}{2}\n".format(" "*offset, " "*offset, "-"*6)
        for valve in self._valves:
            status += valve.status(status, offset+2, print_status=False)
        for pressure in self._pressure_switches:
            status += pressure.status(status, offset+2, print_status=False)
                    
        if newline:
            status += "\n"
        if print_status is True:
            print(status)
        else:
            return status

    def open(self):
        """
        Opens all the valves in the vacuum system.
        """
        logging.info("Opening valves in SnD system.")
        for valve in self._valves:
            valve.open()

    def close(self):
        """
        Opens all the valves in the vacuum system.
        """
        logging.info("Closing valves in SnD system.")
        for valve in self._valves:
            valve.close()

    @property
    def valves(self):
        """
        Prints the positions of all the valves in the system.
        """
        for valve in self._valves:
            valve.status()

    @property
    def pressures(self):
        """
        Prints the pressures of all the pressure switches in the system.
        """
        for valve in self._valves:
            valve.status()
            

class SplitAndDelay(SndDevice):
    """
    Hard X-Ray Split and Delay System.

    Components
    ----------
    t1 : DelayTower
        Tower 1 in the split and delay system.

    t4 : DelayTower
        Tower 4 in the split and delay system.

    t2 : ChannelCutTower
        Tower 2 in the split and delay system.

    t3 : ChannelCutTower
        Tower 3 in the split and delay system.

    vacuum : SndVacuum
        Vacuum device object for the system.

    di : HamamatsuXYMotionCamDiode
        Input diode for the system.
    
    dd : HamamatsuXYMotionCamDiode
        Diode between the two delay towers.

    do : HamamatsuXYMotionCamDiode
        Output diode for the system.

    dci : HamamatsuXMotionDiode
        Input diode for the channel cut line.
    
    dcc : HamamatsuXMotionDiode
        Diode between the two channel cut towers.
    
    dco : HamamatsuXMotionDiode
        Input diode for the channel cut line.
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

    # Vacuum
    vacuum = Component(SndVacuum, "")

    # SnD and Delay line diodes
    di = Component(HamamatsuXYMotionCamDiode, ":DIA:DI")
    dd = Component(HamamatsuXYMotionCamDiode, ":DIA:DD")
    do = Component(HamamatsuXYMotionCamDiode, ":DIA:DO")

    # Channel Cut Diodes
    dci = Component(HamamatsuXMotionDiode, ":DIA:DCI")
    dcc = Component(HamamatsuXMotionDiode, ":DIA:DCC")
    dco = Component(HamamatsuXMotionDiode, ":DIA:DCO")
    
    # Constants
    c = 0.299792458             # mm/ps
    gap = 55                    # m
    
    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self.delay_towers = [self.t1, self.t4]
        self.channelcut_towers = [self.t2, self.t3]
        self.towers = self.delay_towers + self.channelcut_towers

    @property
    def theta1(self):
        """
        Returns the bragg angle the the delay line is currently set to
        maximize.

        Returns
        -------
        theta1 : float
            The bragg angle the delay line is currently set to maximize 
            in degrees.
        """
        # Perform any other calculations here
        return self.t1.theta

    @property
    def theta2(self):
        """
        Returns the bragg angle the the delay line is currently set to
        maximize.

        Returns
        -------
        theta2 : float
            The bragg angle the channel cut line is currently set to maximize 
            in degrees.
        """
        # Perform any other calculations here
        return self.t2.theta    

    def delay_to_length(self, delay, theta1=None, theta2=None):
        """
        Converts the inputted delay to the lengths on the delay arm linear
        stages.

        Parameters
        ----------
        delay : float
            The desired delay in picoseconds.

        theta1 : float or None, optional
            Bragg angle the delay line is set to maximize.

        theta2 : float or None, optional
            Bragg angle the channel cut line is set to maximize.

        Returns
        -------
        length : float
            The distance between the delay crystal and the splitting or
            recombining crystal.
        """
        # Check if any other inputs were used
        theta1 = theta1 or self.theta1
        theta2 = theta2 or self.theta2

        # Length calculation
        length = ((delay*self.c/2 + self.gap*(1 - cosd(2*theta2)) /
                   sind(theta2)) / (1 - cosd(2*theta1)))
        return length

    def length_to_delay(self, L=None, theta1=None, theta2=None):
        """
        Converts the inputted L of the delay stage, theta1 and theta2 to
        the expected delay of the system, or uses the current positions
        as inputs.

        Parameters
        ----------
        L : float or None, optional
            Position of the linear delay stage.
        
        theta1 : float or None, optional
            Bragg angle the delay line is set to maximize.

        theta2 : float or None, optional
            Bragg angle the channel cut line is set to maximize.

        Returns
        -------
        delay : float
            The delay of the system in picoseconds.
        """
        # Check if any other inputs were used
        L = L or self.t1.L
        theta1 = theta1 or self.theta1
        theta2 = theta2 or self.theta2

        # Delay calculation
        delay = (2*(L*(1 - cosd(2*theta1)) - self.gap*(1 - cosd(2*theta2)) /
                    sind(theta2))/self.c)
        return delay    

    def get_delay_diagnostic_position(self, E1=None, E2=None, delay=None):
        """
        Gets the position the delay diagnostic needs to move to based on the inputted
        energies and delay or the current bragg angles and current delay of the system.

        Parameters
        ----------
        E1 : float or None, optional
            Energy in eV to use for the delay line. Uses the current energy if None is
            inputted

        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current energy if 
            None is inputted.
        
        delay : float or None, optional
            Delay in picoseconds to use for the calculation. Uses current delay if
            None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the inputted
            parameters.
        """
        # Use current bragg angle
        if E1 is None:
            theta1 = self.theta1
        else:
            theta1 = bragg_angle(E=E1)

        # Use current delay stage position if no delay is inputted
        if delay is None:
            length = self.t1.L
        # Calculate the expected delay position if a delay is inputted
        else:
            if E2 is None:
                theta2 = self.theta2
            else:
                theta2 = bragg_angle(E=E2)
            length = self.delay_to_length(delay, theta1=theta1, theta2=theta2)
            
        # Calculate position the diagnostic needs to move to
        position = -length*sind(2*theta1)
        return position

    def get_channelcut_diagnostic_position(self, E2=None):
        """
        Gets the position the channel cut diagnostic needs to move to based on the
        inputted energy or the current energy of the channel cut line.

        Parameters
        ----------
        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current energy if 
            None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the inputted
            parameters.
        """
        # Use the current theta2 of the system or calc based on inputted energy
        if E2 is None:
            theta2 = self.theta2
        else:
            theta2 = bragg_angle(E=E2)
            
        # Calculate position the diagnostic needs to move to
        position = 2*cosd(theta2)*self.gap
        return position
        
    def _apply_tower_move_method(self, position, towers, move_method, wait=False,
                                 *args, **kwargs):
        """
        Runs the inputted aggregate move method on each tower and then optionally
        waits for the move to complete. A move method is defined as being a method
        that returns a status object, or list of status objects.

        Any additional arguments or keyword arguments will be passed to move_method.

        Parmeters
        ---------
        position : float
            Position to pass to the move method.

        towers : list
            List of towers to set the energy for.

        move_method : str
            Method of each tower to run.

        wait : bool, optional
            Wait for each tower to complete the motion.
        """
        # Check that there are no issues moving any of the tower motors        
        status = [getattr(t, move_method)(position, *args, **kwargs) for t in towers]

        # Wait for the motions to finish
        if wait:
            for s in flatten(status):
                logger.info("Waiting for {} to finish move ...".format(s.device.name))
                status_wait(s)
        return status

    def set_energy(self, E, wait=False, *args, **kwargs):
        """
        Sets the energy for both the delay line and the channe cut line of the
        system.

        Parmeters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for each tower to complete the motion.
        """
        # Check that all the tower and diagnostic motors can be moved
        for tower in self.towers:
            tower.check_motors()
        self.dd.x.check_status()
        self.dcc.x.check_status()
        
        # Move the tower motors
        status = self._apply_tower_move_method(
            E, self.towers, "set_energy", wait=False, check_motors=False, *args, **kwargs)

        # Get the pos for the diagnostic motors and move there
        dd_x_pos = self.get_delay_diagnostic_position(E1=E, E2=E)
        dcc_x_pos = self.get_channelcut_diagnostic_position(E2=E)
        status.append(self.dd.x.move(dd_x_pos, wait=False))
        status.append(self.dcc.x.move(dcc_x_pos, wait=False))

        # Optionally wait for all the moves to complete
        if wait:
            for s in flatten(status):
                logger.info("Waiting for {} to finish move ...".format(s.device.name))
                status_wait(s)
        return status
    
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
        system. Alias for set_energy(E).

        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        status = self.set_energy(E)        

    @property
    def E(self):
        """
        Returns the energy the whole system is currently set to in eV. Alias
        for energy.

        Returns
        -------
        E1, E2 : tuple
            Energy for the delay line and channel cut line.
        """
        return self.energy

    @E.setter
    def E(self, E):
        """
        Sets the energy for both the delay line and the channe cut line of the
        system. Alias for set_energy(E).

        Parmeters
        ---------
        E : float
            Energy to use for the system.
        """
        status = self.set_energy(E)
        
    def set_energy1(self, E, wait=False, *args, **kwargs):
        """
        Sets the energy for the delay line.

        Parmeters
        ---------
        E : float
            Energy to use for the delay line.

        wait : bool, optional
            Wait for each motor to complete the motion.
        """
        # Check that all the delay tower and diagnostic motors can be moved
        for tower in self.delay_towers:
            tower.check_motors()
        self.dd.x.check_status()
        
        # Move all delay tower motors
        status = self._apply_tower_move_method(
            E, self.delay_towers, "set_energy", wait=False, check_motors=False,
            *args, **kwargs)

        # Get the pos for the diagnostic motor and move there
        dd_x_pos = self.get_delay_diagnostic_position(E1=E, E2=E)
        status.append(self.dd.x.move(dd_x_pos, wait=False))

        # Optionally wait for all the moves to complete
        if wait:
            for s in flatten(status):
                logger.info("Waiting for {} to finish move ...".format(s.device.name))
                status_wait(s)
        return status    

    @property
    def energy1(self):
        """
        Returns the calculated energy based on the angle of the tth motor.

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
        inputted energy. Alias for set_energy(E).
    
        Parmeters
        ---------
        E : float
            Energy to use for the delay line.
        """
        status = self.set_energy1(E)

    @property
    def E1(self):
        """
        Returns the calculated energy based on the angle of the tth motor.

        Returns
        -------
        E1 : float
            Energy of the delay line.
        """
        return self.energy1

    @E1.setter
    def E1(self, E):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy. Alias for set_energy(E).
    
        Parmeters
        ---------
        E : float
            Energy to use for the delay line.
        """
        self.energy1 = E

    def set_energy2(self, E, wait=False, *args, **kwargs):
        """
        Sets the energy for the channel cut line.

        Parmeters
        ---------
        E : float
            Energy to use for the channel cut line.

        wait : bool, optional
            Wait for each motor to complete the motion.
        """
        # Check that all the delay tower and diagnosic motors can be moved
        for tower in self.channelcut_towers:
            tower.check_motors()
        self.dcc.x.check_status()

        # Move all the channel cut tower motors
        status = self._apply_tower_move_method(
            E, self.channelcut_towers, "set_energy", wait=False, check_motors=False
            *args, **kwargs)

        # Get the pos for the diagnostic motors and move there
        dcc_x_pos = self.get_channelcut_diagnostic_position(E2=E)
        status.append(self.dcc.x.move(dcc_x_pos, wait=False))

        # Optionally wait for all the moves to complete
        if wait:
            for s in flatten(status):
                logger.info("Waiting for {} to finish move ...".format(s.device.name))
                status_wait(s)
        return status    
        
    @property
    def energy2(self):
        """
        Returns the calculated energy based on the angle of the th motor on the
        channel cut line.

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
        inputted energy. Alias for set_energy2(E). 
    
        Parmeters
        ---------
        E : float
            Energy to use for the channel cut line.
        """
        status = self.set_energy2(E)

    @property
    def E2(self):
        """
        Returns the calculated energy based on the angle of the th motor on the
        channel cut line.

        Returns
        -------
        E : float
            Energy of the channel cut line.
        """
        return self.energy2

    @E2.setter
    def E2(self, E):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy. Alias for set_energy2(E).
    
        Parmeters
        ---------
        E : float
            Energy to use for the channel cut line.
        """
        self.energy2 = E

    def set_delay(self, delay, wait=False, *args, **kwargs):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions.
        
        Parameters
        ----------
        delay : float
            The desired delay of the system in picoseconds.
        """
        # Check that all the tower motors can be moved
        for tower in self.delay_towers:
            tower.check_motors(energy=False, delay=True)        
        logger.debug("Input delay: {0}. \nMoving t1.L and t2.L to {1}".format(
            t, self.length))

        # Get the delay position to move to
        length = self.delay_to_length(delay)
        
        # Move all the delay stage motors
        status = self._apply_tower_move_method(
            length, self.delay_towers, "set_length", wait=wait, *args, **kwargs)
        return status
    
    @property
    def delay(self):
        """
        Returns the current expected delay of the system.

        Returns
        -------
        delay : float
            Expected delay in picoseconds.
        """
        return self.length_to_delay()
    
    @delay.setter
    def delay(self, delay):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions. Alias for
        set_delay(t).

        Parameters
        ----------
        delay : float
            The desired delay from the system.
        """
        status = self.set_delay(delay)
        
    def status(self):
        """
        Returns the status of the split and delay system.
        
        Returns
        -------
        Status : str            
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
 
