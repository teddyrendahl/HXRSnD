#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aerotech devices
"""
############
# Standard #
############
import logging
import os

###############
# Third Party #
###############
import numpy as np
from ophyd.utils import LimitError
########
# SLAC #
########
from pcdsdevices.epics.epicsmotor import EpicsMotor
from pcdsdevices.component import Component
from pcdsdevices.epics.signal import (EpicsSignal, EpicsSignalRO, FakeSignal)

##########
# Module #
##########
from .exceptions import MotorDisabled, MotorFaulted

logger = logging.getLogger(__name__)


class AeroBase(EpicsMotor):
    """
    Base Aerotech motor class.

    Components
    ----------
    power : EpicsSignal, ".CNEN"
        Enables or disables power to the axis.

    retries : EpicsSignalRO, ".RCNT"
        Number of retries attempted.

    retries_max : EpicsSignal, ".RTRY"
        Maximum number of retries.

    retries_deadband : EpicsSignal, ".RDBD"
        Tolerance of each retry.

    axis_fault : EpicsSignalRO, ":AXIS_FAULT"
        Fault readback for the motor.

    axis_status : EpicsSignalRO, ":AXIS_STATUS"
        Status readback for the motor.

    clear_error : EpicsSignal, ":CLEAR"
        Clear error signal.

    config : EpicsSignal, ":CONFIG"
        Signal to reconfig the motor.
    """
    # Remove when these have been figured out
    low_limit_switch = Component(FakeSignal)
    high_limit_switch = Component(FakeSignal)
    direction_of_travel = Component(FakeSignal)

    power = Component(EpicsSignal, ".CNEN")
    retries = Component(EpicsSignalRO, ".RCNT")
    retries_max = Component(EpicsSignal, ".RTRY")
    retries_deadband = Component(EpicsSignal, ".RDBD")
    axis_status = Component(EpicsSignalRO, ":AXIS_STATUS")
    axis_fault = Component(EpicsSignalRO, ":AXIS_FAULT")
    clear_error = Component(EpicsSignal, ":CLEAR")
    config = Component(EpicsSignal, ":CONFIG")
    zero_all_proc = Component(EpicsSignal, ".ZERO_P.PROC")
    home_forward = Component(EpicsSignal, ".HOMF")
    home_reverse = Component(EpicsSignal, ".HOMR")

    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc=desc
        super().__init__(prefix, *args, **kwargs)
        self.configuration_attrs.append("power")
        if desc is None:
            self.desc = self.name

    def _status_print(self, status, msg=None, ret_status=False, print_set=True):
        """
        Internal method that optionally returns the status object and optionally
        prints a message about the set. If a message is passed but print_set is
        False then the message is logged at the debug level.

        Parameters
        ----------
        status : StatusObject
            The inputted status object.
        
        msg : str or None, optional
            Message to print if print_set is True.

        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            Inputted status object.        
        """
        if msg is not None:
            if print_set:
                logger.info(msg)
            else:
                logger.debug(msg)
        if ret_status:
            return status

    def homf(self, ret_status=False, print_set=True):
        """
        Home the motor forward.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.
        
        Returns
        -------
        Status : StatusObject
            Status of the set.
        """
        status = self.home_forward.set(1)
        return self._status_print(status, "Homing '{0}' forward.".format(
            self.desc))

    def homr(self, ret_status=False, print_set=True):
        """
        Home the motor in reverse.
        
        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status : StatusObject
            Status of the set.
        """
        status = self.home_reverse.set(1)
        return self._status_print(status, "Homing '{0}' in reverse.".format(
            self.desc))

    def move(self, position, wait=False, check_status=True, ret_status=True, 
             print_move=False, *args, **kwargs):
        """
        Move to a specified position, optionally waiting for motion to
        complete.

        Parameters
        ----------
        position
            Position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        ret_status : bool, optional
            Return the status object of the move.

        print_move : bool, optional
            Print a short statement about the move.

        moved_cb : callable
            Call this callback when movement has finished. This callback must
            accept one keyword argument: 'obj' which will be set to this
            positioner instance.

        timeout : float, optional
            Maximum time to wait for the motion. If None, the default timeout
            for this positioner is used.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        
        Raises
        ------
        TimeoutError
            When motion takes longer than `timeout`
        
        ValueError
            On invalid positions
        
        RuntimeError
            If motion fails other than timing out
        """
        try:
            # Check the motor status
            if check_status:
                self.check_status()
            status =  super().move(position, wait=wait, *args, **kwargs)

            # Notify the user that a motor has completed or the command is sent
            if print_move:
                if wait:
                    logger.info("Move completed for '{0}'.".format(self.desc))
                else:
                    logger.info("Move command sent to '{0}'.".format(self.desc))

            # Check if a status object is desired
            if ret_status:
                return status

        # If keyboard interrupted, make sure to stop the motor
        except KeyboardInterrupt:
            self.stop()
            logger.info("Motor '{0}' stopped by keyboard interrupt".format(
                self.desc))
            
        except LimitError:
            logger.info("Requested move '{0}' is outside the soft limits {1}."
                        "".format(position, self.limits))

    def _additional_status_checks(self, *args, **kwargs):
        """
        Placeholder method for any additional status checks that would need to
        be run for this motor. It is meant to be overriden by a higher level
        function.
        """
        pass

    def move_rel(self, rel_position, *args, **kwargs):
        """
        Move relative to the current position, optionally waiting for motion to
        complete.

        Parameters
        ----------
        rel_position
            Relative position to move to

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        ret_status : bool, optional
            Return the status object of the move.

        print_move : bool, optional
            Print a short statement about the move.

        moved_cb : callable
            Call this callback when movement has finished. This callback must
            accept one keyword argument: 'obj' which will be set to this
            positioner instance.

        timeout : float, optional
            Maximum time to wait for the motion. If None, the default timeout
            for this positioner is used.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        
        Raises
        ------
        TimeoutError
            When motion takes longer than `timeout`
        
        ValueError
            On invalid positions
        
        RuntimeError
            If motion fails other than timing out        
        """
        return self.move(rel_position + self.position, *args, **kwargs)

    def mv(self, position, wait=True, ret_status=False, print_move=True, 
           *args, **kwargs):
        """
        Move to a specified position, optionally waiting for motion to
        complete. Alias for move().

        Parameters
        ----------
        position
            Position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        ret_status : bool, optional
            Return the status object of the move.

        print_move : bool, optional
            Print a short statement about the move.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        """
        return self.move(position, wait=wait, ret_status=ret_status, 
                         print_move=print_move, *args, **kwargs)

    def mvr(self, rel_position, wait=True, ret_status=False, print_move=True, 
            *args, **kwargs):
        """
        Move relative to the current position, optionally waiting for motion to
        complete. Alias for move_rel().

        Parameters
        ----------
        rel_position
            Relative position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        ret_status : bool, optional
            Return the status object of the move.

        print_move : bool, optional
            Print a short statement about the move.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        """
        return self.move_rel(rel_position, wait=wait, ret_status=ret_status, 
                             print_move=print_status, *args, **kwargs)

    def check_status(self, *args, **kwargs):
        """
        Checks the status of the motor to make sure it is ready to move.

        Raises
        ------
        MotorDisabled
            If the motor is disabled.
        
        MotorFaulted
            If the motor is faulted.
        """
        if not self.enabled:
            err = "Motor must be enabled before moving."
            logger.error(err)
            raise MotorDisabled(err)

        if self.faulted:
            err = "Motor is currently faulted."
            logger.error(err)
            raise MotorFaulted(err)

        # Run any additional status checks
        self._additional_status_checks(*args, **kwargs)
        
    def set_position(self, position_des):
        """
        Sets the current position to be the inputted position by changing the 
        offset.
        
        Parameters
        ----------
        position_des : float
            The desired current position.
        """
        logger.info("Previous position: {0}, offset: {1}".format(
            self.position, self.offset))
        self.offset += position_des - self.position
        logger.info("New position: {0}, offset: {1}".format(
            self.position, self.offset))

    def enable(self, ret_status=False, print_set=True):
        """
        Enables the motor power.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the power signal.
        """
        status = self.power.set(1)
        return self._status_print(status, "Enabled motor '{0}'.".format(
            self.desc))

    def disable(self, ret_status=False, print_set=True):
        """
        Disables the motor power.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the power signal.
        """
        status = self.power.set(0)
        return self._status_print(status, "Disabled motor '{0}'.".format(
            self.desc))

    @property
    def enabled(self):
        """
        Returns if the motor is curently enabled.

        Returns
        -------
        enabled : bool
            True if the motor is powered, False if not.
        """
        return bool(self.power.value)

    def clear(self, ret_status=False, print_set=True):
        """
        Clears the motor error.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the clear_error signal.
        """
        status = self.clear_error.set(1)
        return self._status_print(status, "Cleared motor '{0}'.".format(
            self.desc))

    def reconfig(self, ret_status=False, print_set=True):
        """
        Re-configures the motor.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the config signal.
        """
        status = self.config.set(1)
        return self._status_print(status, "Reconfigured motor '{0}'.".format(
            self.desc))

    @property
    def faulted(self):
        """
        Returns the current fault with the motor.
        
        Returns
        -------
        faulted
            Fault enumeration.
        """
        return bool(self.axis_fault.value)
    
    def zero_all(self, ret_status=False, print_set=True):
        """
        Sets the current position to be the zero position of the motor.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_move : bool, optional
            Print a short statement about the set.

        Returns
        -------
        status : StatusObject        
            Status object for the set.
        """
        status = self.zero_all_proc.set(1)
        return self._status_print(status, "Zeroed motor '{0}'.".format(
            self.desc))

    def expert_screen(self, print_msg=True):
        """
        Launches the expert screen for the motor.

        Parameters
        ----------
        print_msg : bool, optional
            Prints that the screen is being launched.
        """
        if print_msg:
            logger.info("Launching expert screen.")
        os.system("/reg/neh/operator/xcsopr/bin/snd/expert_screen.sh {0}"
                  "".format(self.prefix))

    def __call__(self, position, wait=True, ret_status=False, print_move=True,
                 *args, **kwargs):
        """
        Moves the motor to the inputted position. Alias for self.move(position).

        Parameters
        ----------
        position
            Position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

        ret_status : bool, optional
            Return the status object of the move.

        print_move : bool, optional
            Print a short statement about the move.

        Returns
        -------
        status : MoveStatus 
            Status object for the move.
        """
        return self.move(position, wait=wait, ret_status=ret_status,
                         print_move=print_move, *args, **kwargs)
    
    def status(self, status="", offset=0, print_status=True, newline=False):
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

        newline : bool, optional
            Adds a new line to the end of the string.

        Returns
        -------
        status : str
            Status string.
        """
        status += "{0}{1}\n".format(" "*offset, self.desc)
        status += "{0}PV: {1:>25}\n".format(" "*(offset+2), self.prefix)
        status += "{0}Enabled: {1:>20}\n".format(" "*(offset+2), 
                                                 str(self.enabled))
        status += "{0}Faulted: {1:>20}\n".format(" "*(offset+2), 
                                                 str(self.faulted))
        status += "{0}Position: {1:>19}\n".format(" "*(offset+2), 
                                                  np.round(self.wm(), 6))
        status += "{0}Limits: {1:>21}\n".format(
            " "*(offset+2), str((int(self.low_limit), int(self.high_limit))))
        if newline:
            status += "\n"
        if print_status is True:
            print(status)
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

    
class RotationAero(AeroBase):
    """
    Class for the aerotech rotation stage.
    """
    pass


class LinearAero(AeroBase):
    """
    Class for the aerotech linear stage.
    """
    pass

    
class DiodeAero(AeroBase):
    """
    VT50 Micronix Motor of the diodes
    """
    pass
