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

##########
# Module #
##########
from .utils import get_logger
from .bragg import bragg_angle, cosd, sind
from .exceptions import MotorDisabled, MotorFaulted, BadN2Pressure

logger = get_logger(__name__, log_file=False)


class MacroBase(Device):
    """
    Base pseudo-motor class for the SnD macro-motions.
    """
    # Constants
    c = 0.299792458             # mm/ps
    gap = 55                    # m

    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc = desc
        super().__init__(prefix, *args, **kwargs)
        
        # Make sure this is used
        if self.parent is None:
            logger.warning("Macromotors must be instantiated with a parent "
                           "that has the SnD towers as components to function "
                           "properly.")
        else:
            self._delay_towers = [self.parent.t1, self.parent.t4]
            self._channelcut_towers = [self.parent.t2, self.parent.t3]
        if self.desc is None:
            self.desc = self.name

    def position(self):
        """
        Returns the current energy of the channel cut line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return (self.parent.t1.energy, self.parent.t2.energy,
                self._length_to_delay())

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
        theta1 = theta1 or self.parent.theta1
        theta2 = theta2 or self.parent.theta2

        # Length calculation
        length = ((delay*self.c/2 + self.gap*(1 - cosd(2*theta2)) /
                   sind(theta2)) / (1 - cosd(2*theta1)))
        return length

    def _get_delay_diagnostic_position(self, E1=None, E2=None, delay=None):
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
            theta1 = self.parent.theta1
        else:
            theta1 = bragg_angle(E=E1)

        # Use current delay stage position if no delay is inputted
        if delay is None:
            length = self.parent.t1.length
        # Calculate the expected delay position if a delay is inputted
        else:
            if E2 is None:
                theta2 = self.parent.theta2
            else:
                theta2 = bragg_angle(E=E2)
            length = self._delay_to_length(delay, theta1=theta1, theta2=theta2)
            
        # Calculate position the diagnostic needs to move to
        position = -length*sind(2*theta1)
        return position

    def _get_channelcut_diagnostic_position(self, E2=None):
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
            theta2 = self.parent.theta2
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
            for tower in self._delay_towers:
                for motor, position in zip(tower._energy_motors,
                                           tower._get_move_positions(theta1)):
                    string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                        motor.desc, motor.position, position)

        if E2 is not None:
            theta2 = bragg_angle(E=E2)
            for tower in self._delay_towers:
                for motor, position in zip(tower._energy_motors,
                                           tower._get_move_positions(theta1)):
                    string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                        motor.desc, motor.position, position)

        if delay is not None:
            length = self._delay_to_length(delay)
            for tower in self._delay_towers:
                string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                    tower.L.desc, tower.length, length)

        if E1 is not None or delay is not None:
            position_dd = self._get_delay_diagnostic_position(E1, E2, delay)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dd.x", self.parent.dd.x.position, position_dd)
        if E2 is not None:
            position_dcc = self._get_channelcut_diagnostic_position(E2)
            string += "\n{:^15}|{:^15.3f}|{:^15.3f}".format(
                "dcc.x", self.parent.dcc.x.position, position_dcc)
            
        logger.info(string)
        try:
            response = input("\nConfirm Move [y]: ")
        except Exception as e:
            logger.info("Exception raised: {0}".format(e))
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
            for tower in self._delaytowers:
                tower.check_status(energy=E1, length=length)

            # Check the delay diagnostic position
            position_dd = self._get_delay_diagnostic_position(E1=E1, E2=E2, 
                                                             delay=delay)
            self.parent.dd.x.check_status(position_dd)
            
        # Check channel cut line
        if E2 is not None:
            # Check each of the channel cut towers
            for tower in self._channelcut_towers:
                tower.check_status(energy=E2)

            # Check the channel cut diagnostic position
            position_dcc = self._get_channelcut_diagnostic_position(E2=E2)
            self.parent.dcc.x.check_status(position_dcc)

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
                       tower in self._delaytowers]
            # Log the energy change
            logger.debug("Setting E1 to {0}.".format(E1))
            
        # Move the channel cut line
        if E2 is not None and position_dcc is not None:
            # Move the channel cut towers
            status += [tower.set_energy(E2, wait=False, check_status=False) for
                       tower in self._channelcut_towers]
            # Move the channel cut diagnostics
            status += [self.parent.dcc.x.move(position_dcc, wait=False)]
            # Log the energy change
            logger.debug("Setting E2 to {0}.".format(E2))
            
        # Move the delay stages
        if delay is not None and length is not None:
            status += [tower.set_length(length, wait=False, check_status=False) 
                       for tower in self._delaytowers]
            # Log the delay change
            logger.debug("Setting delay to {0}.".format(delay))
        
        if ((delay is not None and length is not None) or 
            (E1 is not None and position_dd is not None)):
            # Move the delay diagnostic to the inputted position
            status += [self.parent.dd.x.move(position_dd, wait=False)]

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
            Position to move to for the macro-motor. List follows the form:
            [E1, E2, delay].

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
        status = self.set_system(*position, wait=wait, verify_move=verify_move,
                                 ret_status=ret_status)

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

    def _catch_motor_exceptions(self, clbl, *args, **kwargs):
        """
        Method that runs the inputted callable with the inputted arguments 
        wrapped in a try/except that catches a number of motor exceptions and
        prints to the console a nicer message about what went wrong.

        Parameters
        ----------
        clbl : callable
            Callable to wrap in a try/except.

        args : tuple
            Arguments to pass to the callable.
            
        kwargs : dict
            Key-word arguments to pass to the callable.
            
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
        ret
            Whatever the callable is supposed to return.
        """
        try:
            return clbl(*args, **kwargs)
        
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
        # Perform the move, catching the common motor exceptions
        return self._catch_motor_exceptions(
            self.move, list(position), wait=wait, verify_move=verify_move, 
            ret_status=ret_status)

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
        # Perform the move, catching the common motor exceptions
        return self._catch_motor_exceptions(
            self.move_rel, list(position_rel), wait=wait,
            verify_move=verify_move, ret_status=ret_status)        

    def __call__(self, position, wait=True, ret_status=False, verify_move=True):
        """
        Moves the macro-motor to the inputted position. Alias for 
        self.mv(position).

        Parameters
        ----------
        position
            Position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

        ret_status : bool, optional
            Return the status object of the move.

        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return self.mv(position, wait=wait, ret_status=ret_status,
                       verify_move=verify_move)

    def wm(self):
        """
        Returns the current position of the macro-motor.

        Returns
        -------
        position : float or list
            Position of the macro-motor.
        """
        return self.position

    def set_position(self, E1=None, E2=None, delay=None):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay.
        
        Parameters
        ----------
        E1 : float or None, optional
            Energy to set the delay line to.

        E2 : float or None, optional
            Energy to set the channel cut line to.

        delay : float or None, optional
            Delay to set the delay stages to.
        """
        # Delay line 
        if E1 is not None:
            theta1 = bragg_angle(E=E1)

            # Set position of each E1 motor in each delay tower
            for tower in self._delay_towers:
                for motor, pos in zip(tower._energy_motors,
                                      tower._get_move_positions(theta1)):
                    motor.set_position(pos, print_set=False)

            # Log the set
            logger.debug("Setting positions for E1 to {0}.".format(E1))

        # Channel Cut Line
        if E2 is not None:
            theta2 = bragg_angle(E=E2)

            # Set position of each E2 motor in each channel cut tower
            for tower in self._channelcut_towers:
                for motor, pos in zip(tower._energy_motors,
                                      tower._get_move_positions(theta1)):
                    motor.set_position(pos, print_set=False)
                    
            # Move the cc diagnostic as well
            position_dcc = self._get_channelcut_diagnostic_position(E2)
            self.parent.dcc.x.set_position(position_dcc, print_set=False)
            
            # Log the set
            logger.debug("Setting positions for E2 to {0}.".format(E2))
            
        # Delay stages
        if delay is not None:
            length = self._delay_to_length(delay)

            # Set the position of each delay stage
            for tower in self._delay_towers:
                tower.L.set_position(length, print_set=False)
                
            # Log the set
            logger.debug("Setting positions for delay to {0}.".format(delay))
            
        # Diagnostic
        if E1 is not None or delay is not None:
            position_dd = self._get_delay_diagnostic_position(E1, E2, delay)
            self.parent.dd.x.set_position(position_dd, print_set=False)            

    def status(self, status="", offset=0, print_status=True, newline=False, 
               short=False):
        """
        Returns the status of the device.
        
        Parameters
        ----------
        status : str, optional
            The string to append the status to.
            
        offset : int, optional
            Amount to offset each line of the status.

        print_status : bool, optional
            Determines whether the string is printed or returned.
        """
        status += "\n{0}{1:<16} {2:^16.3f}".format(
            " "*offset, self.desc+":", self.position)

        if newline:
            status += "\n"
        if print_status:
            logger.info(status)
        else:
            return status        
        
    def __repr__(self):
        """
        Returns the status of the motor. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)    


class EnergyMacro(MacroBase):
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
        return super().move([E, E, None], wait=wait, verify_move=verify_move, 
                            ret_status=ret_status)

    def position(self):
        """
        Returns the current energy of the system.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self.parent.t1.energy, self.parent.t2.energy

    def set_position(self, E):
        """
        Sets the positions of the delay and channel cut branches.

        E : float
            Energy to set the system to.
        """
        logger.info("Setting positions for Energy to {0}.".format(E))
        super().set_position(E1=E, E2=E)


class Energy1Macro(MacroBase):
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
        return super().move([E1, None, None], wait=wait,
                            verify_move=verify_move, ret_status=ret_status)

    def position(self):
        """
        Returns the current energy of the delay line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self.parent.t1.energy

    def set_position(self, E1):
        """
        Sets the positions of the delay branch.

        E1 : float
            Energy to set the delay branch to.
        """
        logger.info("Setting positions for Energy 1 to {0}.".format(E1))
        super().set_position(E1=E1)    


class Energy2Macro(MacroBase):
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
        return super().move([None, E2, None], wait=wait,
                            verify_move=verify_move, ret_status=ret_status)

    def position(self):
        """
        Returns the current energy of the channel cut line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self.parent.t2.energy

    def set_position(self, E2):
        """
        Sets the positions of the channel cut branches.

        E2 : float
            Energy to set the channel cut branch to.
        """
        logger.info("Setting positions for Energy 2 to {0}.".format(E2))
        super().set_position(E2=E2)


class DelayMacro(MacroBase):
    """
    Pseudo-motor for the delay macro-motor.
    """
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
        return super().move([None, None, delay], wait=wait,
                            verify_move=verify_move, ret_status=ret_status)

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
        L = L or self.parent.t1.length
        theta1 = theta1 or self.parent.theta1
        theta2 = theta2 or self.parent.theta2

        # Delay calculation
        delay = (2*(L*(1 - cosd(2*theta1)) - self.gap*(1 - cosd(2*theta2)) /
                    sind(theta2))/self.c)
        return delay

    def position(self):
        """
        Returns the current energy of the channel cut line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self._length_to_delay()
    
    def set_position(self, delay):
        """
        Sets the positions of the delay stages.

        delay : float
            Delay to set the delay stages to in ps.
        """
        logger.info("Setting positions for delay stages to {0}.".format(delay))
        super().set_position(delay=delay)

