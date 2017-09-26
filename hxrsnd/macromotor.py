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
from ophyd.utils import LimitError
from ophyd.status import wait as status_wait

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
from .exceptions import MotorDisabled, MotorFaulted, BadN2Pressure


class MacroBase(Device):
    """
    Base pseudo-motor class for the SnD macro-motions.
    """
    # Constants
    c = 0.299792458             # mm/ps
    gap = 55                    # m

    def _delay_to_length(self, delay, theta1=None, theta2=None):
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
            length = self._delay_to_length(delay, theta1=theta1, theta2=theta2)
            
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
            length = self._delay_to_length(delay)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t1.L", self.t1.length, length)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "t4.L", self.t4.length, length)

        if E1 is not None or delay is not None:
            position_dd = self.get_delay_diagnostic_position(E1, E2, delay)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dd.x", self.dd.x.position, position_dd)
        if E2 is not None:
            position_dcc = self.get_channelcut_diagnostic_position(E2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dcc.x", self.dcc.x.position, position_dcc)
            
        logger.info(string)
        try:
            response = input("\nConfirm Move [y]: ")
        except:
            response = "n"

        if response.lower() != "y":
            logger.info("\nMove cancelled.")
            return True
        else:
            logger.debug("\nMove confirmed.")
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
        if E1 is not None or delay is not None:
            # Get the desired length for the delay stage
            if delay is not None:
                length = self._delay_to_length(delay)

            # Check each of the delay towers
            for tower in self.delay_towers:
                tower.check_status(energy=E1, length=length)

            # Check the delay diagnostic position
            position_dd = self.get_delay_diagnostic_position(E1=E1, E2=E2, 
                                                             delay=delay)
            self.dd.x.check_status(position_dd)
            
        # Check channel cut line
        if E2 is not None:
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
            status += [tower.set_length(length, wait=False, check_status=False) 
                       for tower in self.delay_towers]
            # Log the delay change
            logger.debug("Setting delay to {0}.".format(delay))

        
        if ((delay is not None and length is not None) or 
            (E1 is not None and position_dd is not None)):
            # Move the delay diagnostic to the inputted position
            status += [self.dd.x.move(position_dd, wait=False)]

        return status        

    def set_system(self, E1=None, E2=None, delay=None, wait=True, 
                    verify_move=True, ret_status=True):
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

        ret_status : bool, optional
            Return the status object of the move.
        
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
            logger.info("\nMove completed.")
            
        # Optionally return the status
        if ret_status:
            return status

    def move(self, position, wait=True, verify_move=True, ret_status=True):
        """
        Moves the macro parameters to the inputted positions. For energy, this 
        moves the energies of both lines, energy1 moves just the delay line, 
        energy2 moves just the channel cut line, and delay moves just the delay 
        motors.

        Parameters
        ----------
        position : float or list
            Position to move to for the macro-motor. Can be a float or a list 
            depending on the class.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        status = self.set_system(*position, wait=wait, verify_move=verify_move)
        

    def move_rel(self, position_rel, wait=True, verify_move=True, 
                 ret_status=True):
        """
        Performs a relative moves of the macro parameters.  For energy, this 
        moves the energies of both lines, energy1 moves just the delay line, 
        energy2 moves just the channel cut line, and delay moves just the delay 
        motors.

        Parameters
        ----------
        position_rel : float or list
            Relative move for the macro-motor. Can be a float or a list 
            depending on the class.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        # Make sure it is a list
        position_rel = list(position_rel)
        
        # Make the list of abolsute positions to move to
        position = [pos + pos_rel for pos, pos_rel in zip(self.position, 
                                                          position_rel)]

        # Perform the move
        return self.move(position, wait=wait, verify_move=verify_move,
                         ret_status=ret_status)


    def mv(self, position, wait=True, verify_move=True, ret_status=False):
        """
        Moves the macro parameters to the inputted positions. For energy, this 
        moves the energies of both lines, energy1 moves just the delay line, 
        energy2 moves just the channel cut line, and delay moves just the delay 
        motors.
        
        mv() is different from move() by catching all the common exceptions that
        this motor can raise and just raises a logger warning. Therefore if 
        building higher level functionality, do not use this method and use 
        move() instead, otherwise none of the exceptions will propagate beyond
        this method.

        Parameters
        ----------
        position : float or list
            Position to move the macro to.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Exceptions Caught
        -----------------
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
        status : list
            List of status objects for each motor that was involved in the move.
        """
        # Cast position as a list
        position = list(position)        
        try:
            return self.move(*position, wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)
        # Catch all the common motor exceptions        
        except LimitError:
            logger.warning("Requested move '{0}' is outside the soft limits "
                           "{1}.".format(position, self.limits))
        except MotorDisabled:
            logger.warning("Cannot move - motor is currently disabled. Try "
                           "running 'motor.enable()'.")
        except MotorFaulted:
            logger.warning("Cannot move - motor is currently faulted. Try "
                           "running 'motor.clear()'.")
        except BadN2Pressure:
            logger.warning("Cannot move - pressure in tower {0} is bad.".format(
                self._tower))

    def mvr(self, position_rel, wait=True, verify_move=True, ret_status=False):
        """        
        Performs a relative moves of the macro parameters.  For energy, this 
        moves the energies of both lines, energy1 moves just the delay line, 
        energy2 moves just the channel cut line, and delay moves just the delay 
        motors.

        Catches all the same exceptions that mv() does. If a relative move is 
        needed for higher level functions use move_rel() instead.

        
        Parameters
        ----------
        position : float or list
            Position to move the macro to.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Exceptions Caught
        -----------------
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
        status : list
            List of status objects for each motor that was involved in the move.
        """
        # Cast relative position as a list
        position_rel = list(position_rel)       
        try:
            return self.move_rel(position_rel, wait=wait, ret_status=ret_status,
                                 verify_move=verify_move)
        # Catch all the common motor exceptions        
        except LimitError:
            logger.warning("Requested move '{0}' is outside the soft limits "
                           "{1}.".format(position, self.limits))
        except MotorDisabled:
            logger.warning("Cannot move - motor is currently disabled. Try "
                           "running 'motor.enable()'.")
        except MotorFaulted:
            logger.warning("Cannot move - motor is currently faulted. Try "
                           "running 'motor.clear()'.")
        except BadN2Pressure:
            logger.warning("Cannot move - pressure in tower {0} is bad.".format(
                self._tower))


class Energy(MacroBase):
    """
    Pseudo-motor for the energy macro-motor.
    """
    def move(self, E, wait=True, verify_move=True, ret_status=True):
        """
        Moves the macro parameters to the inputted positions.

        Parameters
        ----------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return super().move(E1=E, E2=E, wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)


class Energy1(MacroBase):
    """
    Pseudo-motor for the energy 1 macro-motor.
    """
    def move(self, E1, wait=True, verify_move=True, ret_status=True):
        """
        Moves the macro parameters to the inputted positions.

        Parameters
        ----------
        E1 : float
            Energy to use for the delay line.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return super().move(E1=E1, wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)


class Energy2(MacroBase):
    """
    Pseudo-motor for the energy 2 macro-motor.
    """
    def move(self, E2, wait=True, verify_move=True, ret_status=True):
        """
        Moves the macro parameters to the inputted positions.

        Parameters
        ----------
        E2 : float
            Energy to use for the channel cut line.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return super().move(E2=E2, wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)


class Delay(MacroBase):
    """
    Pseudo-motor for the delay macro-motor.
    """
    def _length_to_delay(self, L=None, theta1=None, theta2=None):
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

    def move(self, delay, wait=True, verify_move=True, ret_status=True):
        """
        Moves the macro parameters to the inputted positions.

        Parameters
        ----------
        delay : float
            Delay to set the system to.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return super().move(delay=delay, wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)

