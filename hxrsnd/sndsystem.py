"""
Script to hold the split and delay class.

All units of time are in picoseconds, units of length are in mm.
"""
############
# Standard #
############
import os
import logging

###############
# Third Party #
###############
import numpy as np
from ophyd.status import wait as status_wait
from ophyd.utils.epics_pvs import raise_if_disconnected

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.component import Component

##########
# Module #
##########
from .state import OphydMachine
from .pneumatic import SndPneumatics
from .utils import flatten, get_logger
from .bragg import bragg_angle, cosd, sind
from .tower import DelayTower, ChannelCutTower
from .diode import HamamatsuXMotionDiode, HamamatsuXYMotionCamDiode

logger = get_logger(__name__)

class SplitAndDelay(Device):
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

    ab : SndPneumatics
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

    # Pneumatic Air Bearings
    ab = Component(SndPneumatics, "")

    # SnD and Delay line diodes
    di = Component(HamamatsuXMotionDiode, ":DIA:DI")
    dd = Component(HamamatsuXYMotionCamDiode, ":DIA:DD")
    do = Component(HamamatsuXMotionDiode, ":DIA:DO")

    # Channel Cut Diodes
    dci = Component(HamamatsuXMotionDiode, ":DIA:DCI")
    dcc = Component(HamamatsuXYMotionCamDiode, ":DIA:DCC")
    dco = Component(HamamatsuXMotionDiode, ":DIA:DCO")
    
    # Constants
    c = 0.299792458             # mm/ps
    gap = 55                    # m
    
    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc = desc
        super().__init__(prefix, *args, **kwargs)
        self.delay_towers = [self.t1, self.t4]
        self.channelcut_towers = [self.t2, self.t3]
        self.towers = self.delay_towers + self.channelcut_towers
        if self.desc is None:
            self.desc = self.name    

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
        L = L or self.t1.length
        theta1 = theta1 or self.theta1
        theta2 = theta2 or self.theta2

        # Delay calculation
        delay = (2*(L*(1 - cosd(2*theta1)) - self.gap*(1 - cosd(2*theta2)) /
                    sind(theta2))/self.c)
        return delay    

    def get_delay_diagnostic_position(self, E1=None, E2=None, delay=None):
        """
        Gets the position the delay diagnostic needs to move to based on the 
        inputted energies and delay or the current bragg angles and current 
        delay of the system.

        Parameters
        ----------
        E1 : float or None, optional
            Energy in eV to use for the delay line. Uses the current energy if 
            None is inputted.

        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current 
            energy if None is inputted.
        
        delay : float or None, optional
            Delay in picoseconds to use for the calculation. Uses current delay
            if None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the 
            inputted parameters.
        """
        # Use current bragg angle
        if E1 is None:
            theta1 = self.theta1
        else:
            theta1 = bragg_angle(E=E1)

        # Use current delay stage position if no delay is inputted
        if delay is None:
            length = self.t1.length
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
        Gets the position the channel cut diagnostic needs to move to based on 
        the inputted energy or the current energy of the channel cut line.

        Parameters
        ----------
        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current 
            energy if None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the 
            inputted parameters.
        """
        # Use the current theta2 of the system or calc based on inputted energy
        if E2 is None:
            theta2 = self.theta2
        else:
            theta2 = bragg_angle(E=E2)
            
        # Calculate position the diagnostic needs to move to
        position = 2*cosd(theta2)*self.gap
        return position

    def _verify_move(self, E1=None, E2=None, delay=None):
        """
        Prints a summary of the current positions and the proposed positions
        of the motors based on the inputs. It then prompts the user to confirm
        the move.
        
        Parameters
        ----------
        E1 : float or None, optional
            The expected E1 for the move.

        E2 : float or None, optional
            The expected E2 for the move.

        delay : float or None, optional
            The expected delay of the move.

        Returns
        -------
        allowed : bool
            True if the move is approved, False if the move is not.
        """
        string = "\n{:^15}|{:^15}|{:^15}".format("Motor", "Current", "Proposed")
        string += "\n" + "-"*len(string)
        if E1 is not None:
            theta1 = bragg_angle(E=E1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t1.tth", self.t1.tth.position, 2*theta1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t4.tth", self.t4.tth.position, 2*theta1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t1.th1", self.t1.th1.position, theta1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t1.th2", self.t1.th2.position, theta1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t4.th1", self.t4.th1.position, theta1)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t4.th2", self.t4.th2.position, theta1)

        if E2 is not None:
            theta2 = bragg_angle(E=E2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t2.th", self.t2.th.position, theta2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t3.th", self.t3.th.position, theta2)

        if delay is not None:
            length = self.delay_to_length(delay)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t1.L", self.t1.length, length)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t4.L", self.t4.length, length)

        if E1:
            position_dd = self.get_delay_diagnostic_position(E1, E2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dd.x", self.dd.x.position, position_dd)
        if E2:
            position_dcc = self.get_channelcut_diagnostic_position(E2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dcc.x", self.dcc.x.position, position_dcc)
            
        logger.info(string)
        response = input("\nConfirm Move [y]: ")
        if response.lower() != "y":
            logger.debug("Move confirmed.")
            return True
        else:
            logger.info("Move cancelled.")
            return False            

    def _check_towers_and_diagnostics(self, E1=None, E2=None, delay=None):
        """
        Checks the towers in the delay line and the channel cut line to make 
        sure they can be moved. Depending on if E1, E2 or delay are entered, 
        the delay line energy motors, channel cut line energy motors or the 
        delay stages will be checked for faults, if they are enabled, if the
        requested energy requires moving beyond the limits and if the pressure
        in the tower N2 is good.

        Parameters
        ----------
        E1 : float or None, optional
            Requested energy for the delay line.

        E2 : float or None, optional
            Requested energy for the channel cut line.

        delay : float or None, optional
            Requested delay for the system.

        Raises
        ------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        length : float or None
            Position to move the delay stages to.

        position_dd : float or None
            Position to move the delay diagnostic to.

        position_dcc : float or None
            Position to move the channel cut diagnostic to.
        """
        length, position_dd, position_dcc = None, None, None
        
        # Check delay line
        if E1 or delay:
            # Get the desired length for the delay stage
            if delay is not None:
                length = self.delay_to_length(delay)

            # Check each of the delay towers
            for tower in self.delay_towers:
                tower.check_status(energy=E1, delay=delay)

            # Check the delay diagnostic position
            position_dd = self.get_delay_diagnostic_position(E1=E1, E2=E2, 
                                                             delay=delay)
            self.dd.x.check_status(position_dd)
            
        # Check channel cut line
        if E2:
            # Check each of the channel cut towers
            for tower in self.channelcut_towers:
                tower.check_status(energy=E2)

            # Check the channel cut diagnostic position
            position_dcc = self.get_channelcut_diagnostic_position(E2=E2)
            self.dcc.x.check_status(position_dcc)

        return length, position_dd, position_dcc

    def _move_towers_and_diagnostics(self, length=None, position_dd=None,
                                     position_dcc=None, E1=None, E2=None, 
                                     delay=None):
        """
        Moves all the tower and diagnostic motors according to the inputted
        energies and delay. If any of the inputted information is set to None
        then that component of the move is ignored.
        
        Parameters
        ----------
        length : float or None, optional
            Position to move the delay stages to.

        position_dd : float or None, optional
            Position to move the delay diagnostic to.

        position_dcc : float or None, optional
            Position to move the channel cut diagnostic to.

        E1 : float or None, optional
            Requested energy for the delay line.

        E2 : float or None, optional
            Requested energy for the channel cut line.

        delay : float or None, optional
            Requested delay for the system.

        Returns
        -------
        status : list
            Nested list of status objects from each tower.
        """
        status = []
        # Move the delay line
        if E1 is not None and position_dd is not None:
            # Move the towers to the specified energy
            status += [tower.set_energy(E1, wait=False, check_status=False) for
                       tower in self.delay_towers]
            # Move the delay diagnostic to the inputted position
            status += [self.dd.x.move(position_dd, wait=False)]
            # Log the energy change
            logger.debug("Setting E1 to {0}.".format(E1))
            
        # Move the channel cut line
        if E2 is not None and position_dcc is not None:
            # Move the channel cut towers
            status += [tower.set_energy(E2, wait=False, check_status=False) for
                       tower in self.channelcut_towers]
            # Move the channel cut diagnostics
            status += [self.dcc.x.move(position_dcc, wait=False)]
            # Log the energy change
            logger.debug("Setting E2 to {0}.".format(E2))
            
        # Move the delay stages
        if delay is not None and length is not None:
            status += [tower.set_delay(length, wait=False, check_status=False) 
                       for tower in self.delay_towers]
            # Log the delay change
            logger.debug("Setting delay to {0}.".format(delay))

        return status        

    def set_system(self, E1=None, E2=None, delay=None, wait=False, 
                    verify_move=True):
        """
        High level system parameter setter. From this function the energies of
        the delay and channel cut lines, as well as the system delay can be
        changed. For any missing inputs, the current state of the system will be
        assumed.

        Parameters
        ----------
        E1 : float or None, optional
            Requested energy for the delay line.

        E2 : float or None, optional
            Requested energy for the channel cut line.

        delay : float or None, optional
            Requested delay for the system.
            
        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.
        
        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        # Prompt the user about the move before making it
        if verify_move and self._verify_move(E1=E1, E2=E2, delay=delay):
            return

        # Check the towers and diagnostics
        length, position_dd, position_dcc = self._check_towers_and_diagnostics(
            E1, E2, delay)

        # Send the move commands to all the motors
        status = flatten(self._move_towers_and_diagnostics(
            length, position_dd, position_dcc, E1, E2, delay))
            
        # Wait for all the motors to finish moving
        if wait:
            logger.info("Waiting for the motors to finish moving...")
            for s in status:
                status_wait(s)
            logger.info("Move completed.")
            
        return status

    def set_energy(self, E, wait=False, verify_move=True, *args, **kwargs):
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
        return self.set_system(E1=E, E2=E)
            
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
        
    def set_energy1(self, E, wait=False, verify_move=True, *args, **kwargs):
        """
        Sets the energy for the delay line.

        Parmeters
        ---------
        E : float
            Energy to use for the delay line.

        wait : bool, optional
            Wait for each motor to complete the motion.
        """
        return self.set_system(E1=E, wait=wait, verify_move=verify_move, *args,
                                **kwargs)

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

    def set_energy2(self, E, wait=False, verify_move=True, *args, **kwargs):
        """
        Sets the energy for the channel cut line.

        Parmeters
        ---------
        E : float
            Energy to use for the channel cut line.

        wait : bool, optional
            Wait for each motor to complete the motion.
        """
        return self.set_system(E2=E, wait=wait, verify_move=verify_move, *args,
                                **kwargs)
        
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

    def set_delay(self, delay, wait=False, verify_move=True, *args, **kwargs):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions.
        
        Parameters
        ----------
        delay : float
            The desired delay of the system in picoseconds.
        """
        return self.set_system(delay=delay, wait=wait, verify_move=verify_move,
                                *args, **kwargs)
    
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

    def main_screen(self):
        """
        Launches the main SnD screen.
        """
        os.system("/reg/neh/operator/xcsopr/bin/snd/snd_main")
        
    def status(self, print_status=True):
        """
        Returns the status of the split and delay system.
        
        Returns
        -------
        Status : str            
        """
        status =  "Split and Delay System Status\n"
        status += "-----------------------------\n"
        status += "  Energy 1: {:>10.3f}\n".format(self.energy1)
        status += "  Energy 2: {:>10.3f}\n".format(self.energy2)
        status += "  Delay:    {:>10.3f}\n".format(self.delay)
        status = self.t1.status(status, 0, print_status=False, newline=True)
        status = self.t2.status(status, 0, print_status=False, newline=True)
        status = self.t3.status(status, 0, print_status=False, newline=True)
        status = self.t4.status(status, 0, print_status=False, newline=True)
        status = self.ab.status(status, 0, print_status=False, newline=False)

        if print_status:
            logger.info(status)
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

# Notes:
# Add the limits for the attocubes to autosave
# Create energy motors

