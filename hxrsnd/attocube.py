"""
Attocube devices
"""
import os
import logging

import numpy as np
from ophyd import PositionerBase
from ophyd import Component as Cmp
from ophyd.utils import LimitError
from ophyd.signal import EpicsSignal, EpicsSignalRO
from ophyd.status import wait as status_wait

from .sndmotor import SndMotor
from .snddevice import SndDevice
from .exceptions import MotorDisabled, MotorError
from .utils import absolute_submodule_path, as_list

logger = logging.getLogger(__name__)


class EccController(SndDevice):
    """
    ECC Controller
    """
    _firm_day = Cmp(EpicsSignalRO, ":CALC:FIRMDAY")
    _firm_month = Cmp(EpicsSignalRO, ":CALC:FIRMMONTH")
    _firm_year = Cmp(EpicsSignalRO, ":CALC:FIRMYEAR")
    _flash = Cmp(EpicsSignal, ":RDB:FLASH", write_pv=":CMD:FLASH")
    
    @property 
    def firmware(self):
        """
        Returns the firmware in the same date format as the EDM screen.
        """
        return "{0}/{1}/{2}".format(
            self._firm_day.value, self._firm_month.value, self._firm_year.value)
    
    @property
    def flash(self):
        """
        Saves the current configuration of the controller.
        """
        return self._flash.set(1, timeout=self.set_timeout)


class EccBase(SndMotor, PositionerBase):
    """
    ECC Motor Class
    """
    # position
    user_readback = Cmp(EpicsSignalRO, ":POSITION", auto_monitor=True)
    user_setpoint = Cmp(EpicsSignal, ":CMD:TARGET")

    # limits
    upper_ctrl_limit = Cmp(EpicsSignal, ':CMD:TARGET.HOPR')
    lower_ctrl_limit = Cmp(EpicsSignal, ':CMD:TARGET.LOPR')

    # configuration
    motor_egu = Cmp(EpicsSignalRO, ":UNIT")
    motor_amplitude = Cmp(EpicsSignal, ":CMD:AMPL")
    motor_dc = Cmp(EpicsSignal, ":CMD:DC")
    motor_frequency = Cmp(EpicsSignal, ":CMD:FREQ")

    # motor status
    motor_connected = Cmp(EpicsSignalRO, ":ST_CONNECT")
    motor_enabled = Cmp(EpicsSignalRO, ":ST_ENABLED")
    motor_referenced = Cmp(EpicsSignalRO, ":ST_REFVAL")
    motor_error = Cmp(EpicsSignalRO, ":ST_ERROR")
    motor_is_moving = Cmp(EpicsSignalRO, ":RD_MOVING")
    motor_done_move = Cmp(EpicsSignalRO, ":RD_INRANGE")
    high_limit_switch = Cmp(EpicsSignal, ":ST_EOT_FWD")
    low_limit_switch = Cmp(EpicsSignal, ":ST_EOT_BWD")
    motor_reference_position = Cmp(EpicsSignalRO, ":REF_POSITION")

    # commands
    motor_stop = Cmp(EpicsSignal, ":CMD:STOP")
    motor_reset = Cmp(EpicsSignal, ":CMD:RESET.PROC")
    motor_enable = Cmp(EpicsSignal, ":CMD:ENABLE")

    @property
    def position(self):
        """
        Returns the current position of the motor.

        Returns
        -------
        position : float
            Current position of the motor.
        """
        return self.user_readback.value

    @property
    def reference(self):
        """
        Returns the reference position of the motor.
        
        Returns
        -------
        position : float
            Reference position of the motor.
        """
        return self.motor_reference_position.value

    @property
    def egu(self):
        """
        The engineering units (EGU) for a position

        Returns
        -------
        Units : str
            Engineering units for the position.
        """
        return self.motor_egu.get()

    def _status_print(self, status, msg=None, ret_status=False, print_set=True,
                      timeout=None, wait=True, reraise=False):
        """
        Internal method that optionally returns the status object and optionally
        prints a message about the set. If a message is passed but print_set is
        False then the message is logged at the debug level.

        Parameters
        ----------
        status : StatusObject or list
            The inputted status object.
        
        msg : str or None, optional
            Message to print if print_set is True.

        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        wait : bool, optional
            Wait for the status to complete.

        reraise : bool, optional
            Raise the RuntimeError in the except.

        Returns
        -------
        Status
            Inputted status object.        
        """
        try:
            # Wait for the status to complete
            if wait:
                for s in as_list(status):
                    status_wait(s, timeout)

            # Notify the user
            if msg is not None:
                if print_set:
                    logger.info(msg)
                else:
                    logger.debug(msg)
            if ret_status:
                return status

        # The operation failed for some reason
        except RuntimeError:
            error = "Operation completed, but reported an error."
            logger.error(error)
            if reraise:
                raise

    def enable(self, ret_status=False, print_set=True):
        """
        Enables the motor power.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the power signal.
        """
        status = self.motor_enable.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Enabled motor '{0}'".format(
            self.desc), ret_status=ret_status, print_set=print_set)

    def disable(self, ret_status=False, print_set=True):
        """
        Disables the motor power.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the power signal.
        """
        status = self.motor_enable.set(0, timeout=self.set_timeout)
        return self._status_print(status, "Disabled motor '{0}'".format(
            self.desc), ret_status=ret_status, print_set=print_set)

    @property
    def enabled(self):
        """
        Returns if the motor is curently enabled.

        Returns
        -------
        enabled : bool
            True if the motor is powered, False if not.
        """
        return bool(self.motor_enable.value)

    @property
    def connected(self):
        """
        Returns if the motor is curently connected.

        Returns
        -------
        connected : bool
            True if the motor is connected, False if not.
        """
        return bool(self.motor_connected.value)

    @property
    def referenced(self):
        """
        Returns if the motor is curently referenced.

        Returns
        -------
        referenced : bool
            True if the motor is referenced, False if not.
        """
        return bool(self.motor_referenced.value)
    
    @property
    def error(self):
        """
        Returns the current error with the motor.
        
        Returns
        -------
        error : bool
            Error enumeration.
        """
        return bool(self.motor_error.value)

    def reset(self, ret_status=False, print_set=True):
        """
        Sets the current position to be the zero position of the motor.

        Returns
        -------
        status : StatusObject        
            Status object for the set.
        """
        status = self.motor_reset.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Reset motor '{0}'".format(
            self.desc), ret_status=ret_status, print_set=print_set)
    
    def move(self, position, check_status=True, timeout=None, *args, **kwargs):
        """
        Move to a specified position.

        Parameters
        ----------
        position
            Position to move to

        check_status : bool, optional
            Check if the motors are in a valid state to move.

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
        # Check the motor status
        if check_status:
            self.check_status(position)
        logger.debug("Moving {0} to {1}".format(self.name, position))
        # Begin the move process
        return self.user_setpoint.set(position, timeout=timeout)

    def mv(self, position, print_move=True, *args, **kwargs):
        """
        Move to a specified position, optionally waiting for motion to
        complete. mv() is different from move() by catching all the common
        exceptions that this motor can raise and just raises a logger
        warning. Therefore if building higher level functionality, do not
        use this method and use move() instead otherwise none of these
        exceptions will propagate to it.

        Parameters
        ----------
        position
            Position to move to.

        print_move : bool, optional
            Print a short statement about the move.

        Exceptions Caught
        -----------------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        """
        try:
            status =  super().mv(position, *args, **kwargs)

            # Notify the user that a motor has completed or the command is sent
            if print_move:
                logger.info("Move command sent to '{0}'.".format(self.desc))
            # Check if a status object is desired
            return status

        # Catch all the common motor exceptions
        except LimitError:
            logger.warning("Requested move '{0}' is outside the soft limits "
                           "{1} for motor {2}".format(position, self.limits,
                                                      self.desc))
        except MotorDisabled:
            logger.warning("Cannot move - motor {0} is currently disabled. Try "
                           "running 'motor.enable()'.".format(self.desc))
        except MotorFaulted:
            logger.warning("Cannot move - motor {0} is currently faulted. Try "
                           "running 'motor.clear()'.".format(self.desc))

    
    def check_status(self, position=None):
        """
        Checks the status of the motor to make sure it is ready to move. Checks
        the current position of the motor, and if a position is provided it also
        checks that position.

        Parameters
        ----------
        position : float
            Position to check for validity.

        Raises
        ------
        MotorDisabled
            If the motor is disabled.

        MotorError
            If the motor has an error.
        """
        if not self.enabled:
            err = "Motor '{0}' is currently disabled.".format(self.desc)
            logger.error(err)
            raise MotorDisabled(err)

        if self.error:
            err = "Motor '{0}' currently has an error.".format(self.desc)
            logger.error(err)
            raise MotorError(err)

        # Check if the current position is valid
        self.check_value(self.position)
        # Check if the move position is valid
        if position: 
            self.check_value(position)

    def check_value(self, position):
        """
        Checks to make sure the inputted value is valid.

        Parameters
        ----------
        position : float
            Position to check for validity

        Raises
        ------
        ValueError
            If position is None, NaN or Inf
        LimitError
            If the position is outside the soft limits.
        """
        # Check for invalid positions
        if position is None or np.isnan(position) or np.isinf(position):
            raise ValueError("Invalid value inputted: '{0}'".format(position))

        # Check if it is within the soft limits
        if not (self.low_limit <= position <= self.high_limit):
            err_str = "Requested value {0} outside of range: [{1}, {2}]"
            logger.warn(err_str.format(position, self.low_limit,
                                       self.high_limit))
            raise LimitError(err_str)

    def stop(self, success=False, ret_status=False, print_set=True):
        """
        Stops the motor.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status : StatusObject
            Status of the set.
        """
        status = self.motor_stop.set(1, wait=False, timeout=self.set_timeout)
        super().stop(success=success)
        return self._status_print(status, "Stopped motor '{0}'".format(
            self.desc), ret_status=ret_status, print_set=print_set)        

    def expert_screen(self, print_msg=True):
        """
        Launches the expert screen for the motor.

        Parameters
        ----------
        print_msg : bool, optional
            Prints that the screen is being launched.
        """
        # Get the absolute path to the screen
        path = absolute_submodule_path("hxrsnd/screens/motor_expert_screens.sh")
        if print_msg:
            logger.info("Launching expert screen.")
        os.system("{0} {1} {2} &".format(path, self.prefix, "attocube"))

    def set_limits(self, llm, hlm):
        """
        Sets the limits of the motor. Alias for limits = (llm, hlm).
        
        Parameters
        ----------
        llm : float
            Desired low limit.
            
        hlm : float
            Desired low limit.
        """        
        self.limits = (llm, hlm)

    @property
    def high_limit(self):
        """
        Returns the upper limit fot the user setpoint.

        Returns
        -------
        high_limit : float
        """
        return self.upper_ctrl_limit.value

    @high_limit.setter
    def high_limit(self, value):
        """
        Sets the high limit for user setpoint.
        """
        self.upper_ctrl_limit.put(value)

    @property
    def low_limit(self):
        """
        Returns the lower limit fot the user setpoint.

        Returns
        -------
        low_limit : float
        """
        return self.lower_ctrl_limit.value

    @low_limit.setter
    def low_limit(self, value):
        """
        Sets the high limit for user setpoint.
        """
        self.lower_ctrl_limit.put(value)

    @property
    def limits(self):
        """
        Returns the limits of the motor.

        Returns
        -------
        limits : tuple
        """
        return (self.low_limit, self.high_limit)

    @limits.setter
    def limits(self, value):
        """
        Sets the limits for user setpoint.
        """
        self.low_limit = value[0]
        self.high_limit = value[1]

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

        newline : bool, optional
            Adds a new line to the end of the string.

        Returns
        -------
        status : str
            Status string.
        """
        if short:
            status += "\n{0}{1:<16}|{2:^16.3f}|{3:^16.3f}".format(
                " "*offset, self.desc, self.position, self.reference)
        else:
            status += "{0}{1}\n".format(" "*offset, self.desc)
            status += "{0}PV: {1:>25}\n".format(" "*(offset+2), self.prefix)
            status += "{0}Enabled: {1:>20}\n".format(" "*(offset+2), 
                                                     str(self.enabled))
            status += "{0}Faulted: {1:>20}\n".format(" "*(offset+2), 
                                                     str(self.error))
            status += "{0}Position: {1:>19}\n".format(" "*(offset+2), 
                                                      np.round(self.wm(), 6))
            status += "{0}Limits: {1:>21}\n".format(
                " "*(offset+2), str((int(self.low_limit), int(self.high_limit))))
        if newline:
            status += "\n"
        if print_status is True:
            logger.info(status)
        else:
            return status


class TranslationEcc(EccBase):
    """
    Class for the translation ecc motor
    """
    pass


class GoniometerEcc(EccBase):
    """
    Class for the goniometer ecc motor
    """
    pass


class DiodeEcc(EccBase):
    """
    Class for the diode insertion ecc motor
    """
    pass
