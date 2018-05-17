"""
Aerotech devices
"""
import logging
import os

import numpy as np
from ophyd import Component as Cmp, FormattedComponent as FrmCmp
from ophyd.utils import LimitError
from ophyd.signal import EpicsSignal, EpicsSignalRO, Signal
from ophyd.status import wait as status_wait

from .sndmotor import SndEpicsMotor
from .pneumatic import PressureSwitch
from .utils import absolute_submodule_path, as_list, stop_on_keyboardinterrupt
from .exceptions import MotorDisabled, MotorFaulted, MotorStopped, BadN2Pressure

logger = logging.getLogger(__name__)


class AeroBase(SndEpicsMotor):
    """
    Base Aerotech motor class.

    Components

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
    low_limit_switch = Cmp(Signal)
    high_limit_switch = Cmp(Signal)

    power = Cmp(EpicsSignal, ".CNEN")
    retries = Cmp(EpicsSignalRO, ".RCNT")
    retries_max = Cmp(EpicsSignal, ".RTRY")
    retries_deadband = Cmp(EpicsSignal, ".RDBD")
    axis_status = Cmp(EpicsSignalRO, ":AXIS_STATUS")
    axis_fault = Cmp(EpicsSignalRO, ":AXIS_FAULT")
    clear_error = Cmp(EpicsSignal, ":CLEAR")
    config = Cmp(EpicsSignal, ":CONFIG")
    zero_all_proc = Cmp(EpicsSignal, ":ZERO_P.PROC")
    home_forward = Cmp(EpicsSignal, ".HOMF")
    home_reverse = Cmp(EpicsSignal, ".HOMR")
    dial = Cmp(EpicsSignalRO, ".DRBV")
    state_component = Cmp(EpicsSignal, ".SPMG")

    def __init__(self, prefix, name=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.motor_done_move.unsubscribe(self._move_changed)
        self.user_readback.unsubscribe(self._pos_changed)
        self.configuration_attrs.append("power")
        self._state_list = ["Stop", "Pause", "Move", "Go"]

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

    @stop_on_keyboardinterrupt
    def homf(self, ret_status=False, print_set=True, check_status=True):
        """
        Home the motor forward.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.
        
        check_status : bool, optional
            Check if the motors are in a valid state to move.

        Returns
        -------
        Status : StatusObject
            Status of the set.
        """        
        # Check the motor status
        if check_status:
            self.check_status()
        status = self.home_forward.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Homing '{0}' forward.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

    @stop_on_keyboardinterrupt
    def homr(self, ret_status=False, print_set=True, check_status=True):
        """
        Home the motor in reverse.
        
        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        Returns
        -------
        Status : StatusObject
            Status of the set.
        """
        # Check the motor status
        if check_status:
            self.check_status()
        status = self.home_reverse.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Homing '{0}' in reverse.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

    def move(self, position, wait=False, check_status=True, timeout=None, *args, 
             **kwargs):
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
        # Check the motor status
        if check_status:
            self.check_status(position)
        logger.debug("Moving {0} to {1}".format(self.name, position))
        return super().move(position, wait=wait, timeout=timeout, *args, 
                            **kwargs)

    def mv(self, position, wait=True, print_move=True, *args, **kwargs):
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

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

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

        MotorStopped
            Error raised if the motor is stopped and the move is requested.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        """
        try:
            status = super().mv(position, wait=wait, *args, **kwargs)

            # Notify the user that a motor has completed or the command is sent
            if print_move:
                if wait:
                    logger.info("Move completed for '{0}'.".format(self.desc))
                else:
                    logger.info("Move command sent to '{0}'.".format(self.desc))
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
        except MotorStopped:
            logger.warning("Cannot move - motor {0} is currently stopped. Try "
                           "running 'motor.state=\"Go\"'.".format(self.desc))

    def check_status(self, position=None):
        """
        Checks the status of the motor to make sure it is ready to move. Checks
        the current position of the motor, and if a position is provided it also
        checks that position.

        Parameters
        ----------
        position : float, optional
            Position to check for validity.

        Raises
        ------
        MotorDisabled
            If the motor is disabled.
        
        MotorFaulted
            If the motor is faulted.

        MotorStopped
            If the motor is stopped.
        """
        if not self.enabled:
            err = "Motor '{0}' is currently disabled".format(self.desc)
            logger.error(err)
            raise MotorDisabled(err)

        if self.faulted:
            err = "Motor '{0}' is currently faulted.".format(self.desc)
            logger.error(err)
            raise MotorFaulted(err)

        if self.state == "Stop":
            err = "Motor '{0}' is currently stopped.".format(self.desc)
            logger.error(err)
            raise MotorStopped(err)
        
        # Check if the current position is valid
        self.check_value(self.position)
        # Check if the move position is valid
        if position: 
            self.check_value(position)
        
    def set_position(self, position_des, print_set=True):
        """
        Sets the current position to be the inputted position by changing the 
        offset.
        
        Parameters
        ----------
        position_des : float
            The desired current position.
        """
        # Print to console or just to the log
        if print_set:
            log_level = logger.info
        else:
            log_level = logger.debug
        
        log_level("'{0}' previous position: {0}, offset: {1}".format(
            self.position, self.offset))
        self.offset += position_des - self.position
        log_level("'{0}' New position: {0}, offset: {1}".format(self.position,
                                                                self.offset))

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
        status = self.power.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Enabled motor '{0}'.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

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
        status = self.power.set(0, timeout=self.set_timeout)
        return self._status_print(status, "Disabled motor '{0}'.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

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

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the clear_error signal.
        """
        status = self.clear_error.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Cleared motor '{0}'.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

    def reconfig(self, ret_status=False, print_set=True):
        """
        Re-configures the motor.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the config signal.
        """
        status = self.config.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Reconfigured motor '{0}'.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

    @property
    def faulted(self):
        """
        Returns the current fault with the motor.
        
        Returns
        -------
        faulted
            Fault enumeration.
        """
        if self.axis_fault.connected:
            return bool(self.axis_fault.value)
        else:
            return None
    
    def zero_all(self, ret_status=False, print_set=True):
        """
        Sets the current position to be the zero position of the motor.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        status : StatusObject        
            Status object for the set.
        """
        status = self.zero_all_proc.set(1, timeout=self.set_timeout)
        return self._status_print(status, "Zeroed motor '{0}'.".format(
            self.desc), print_set=print_set, ret_status=ret_status)

    @property
    def state(self):
        """
        Returns the state of the motor. State can be one of the following:
            'Stop', 'Pause', 'Move', 'Go'

        Returns
        -------
        state : str
            The current state of the motor
        """
        return self._state_list[self.state_component.get()]

    @state.setter
    def state(self, val, ret_status=False, print_set=True):
        """
        Sets the state of the motor. Inputted state can be one of the following
        states or the index of the desired state:
            'Stop', 'Pause', 'Move', 'Go'            
        Alias for set_state((val, False, True)
        
        Parameters
        ----------
        val : int or str
        
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the state signal.        
        """
        try:
            return self.set_state(val, ret_status, print_set)
        except ValueError:
            logger.info("State must be one of the following: {0}".format(
                self._state_list))

    def set_state(self, state, ret_status=True, print_set=False):
        """
        Sets the state of the motor. Inputted state can be one of the following
        states or the index of the desired state:
            'Stop', 'Pause', 'Move', 'Go'            
        
        Parameters
        ----------
        val : int or str
        
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for setting the state signal.        
        """
        # Make sure it is in title case if it's a string
        val = state
        if isinstance(state, str):
            val = state.title()

        # Make sure it is a valid state or enum
        if val not in self._state_list + list(range(len(self._state_list))):
            error = "Invalid state inputted: '{0}'.".format(val)
            logger.error(error)
            raise ValueError(error)
        
        # Lets enforce it's a string or value
        status = self.state_component.set(val, timeout=self.set_timeout)

        return self._status_print(
            status, "Changed state of '{0} to '{1}'.".format(self.desc, val), 
            print_set=print_set, ret_status=ret_status)

    def ready_motor(self, ret_status=False, print_set=True):
        """
        Sets the motor to the ready state by clearing any errors, enabling it,
        and setting the state to be 'Go'.

        Parameters
        ----------
        ret_status : bool, optional
            Return the status object of the set.

        print_set : bool, optional
            Print a short statement about the set.

        Returns
        -------
        Status
            The status object for all the sets.        
        """
        status = [self.clear(ret_status=True, print_set=False)]
        status.append(self.enable(ret_status=True, print_set=False))
        status.append(self.set_state("Go", ret_status=True, print_set=False))
        return self._status_print(
            status, "Motor '{0}' is now ready to move.".format(self.desc), 
            print_set=print_set, ret_status=ret_status)

    def expert_screen(self, print_msg=True):
        """
        Launches the expert screen for the motor.

        Parameters
        ----------
        print_msg : bool, optional
            Prints that the screen is being launched.
        """
        path = absolute_submodule_path("hxrsnd/screens/motor_expert_screens.sh")
        if print_msg:
            logger.info("Launching expert screen.")
        os.system("{0} {1} {2} &".format(path, self.prefix, "aerotech"))
     
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
                " "*offset, self.desc, self.position, self.dial.value)
        else:
            status += "{0}{1}\n".format(" "*offset, self.desc)
            status += "{0}PV: {1:>25}\n".format(" "*(offset+2), self.prefix)
            status += "{0}Enabled: {1:>20}\n".format(" "*(offset+2), 
                                                     str(self.enabled))
            status += "{0}Faulted: {1:>20}\n".format(" "*(offset+2), 
                                                     str(self.faulted))
            status += "{0}State: {1:>22}\n".format(" "*(offset+2), 
                                                     str(self.state))
            status += "{0}Position: {1:>19}\n".format(" "*(offset+2), 
                                                      np.round(self.wm(), 6))
            status += "{0}Dial: {1:>23}\n".format(" "*(offset+2), 
                                                      np.round(self.dial.value,
                                                               6))
            status += "{0}Limits: {1:>21}\n".format(
                " "*(offset+2), str((int(self.low_limit), 
                                     int(self.high_limit))))

        if newline:
            status += "\n"
        if print_status is True:
            logger.info(status)
        else:
            return status


class InterlockedAero(AeroBase):
    """
    Linear Aerotech stage that has the additional move check for the pressure
    status.
    """
    # To do the internel pressure check
    _pressure = FrmCmp(PressureSwitch, "{self._prefix}:N2:{self._tower}")

    def __init__(self, prefix, *args, **kwargs):
        self._tower = prefix.split(":")[-2]
        self._prefix = ":".join(prefix.split(":")[:2])
        super().__init__(prefix, *args, **kwargs)

    def check_status(self, *args, **kwargs):
        """
        Status check that also checks if the pressure measured by the pressure
        switch is good.
        
        Parameters
        ----------
        position : float
            Position to check for validity.

        Raises
        ------
        MotorDisabled
            If the motor is disabled.
        
        MotorFaulted
            If the motor is faulted.

        MotorStopped
            If the motor is stopped.

        BadN2Pressure
            If the pressure in the tower is bad.
        """
        if self._pressure.bad:
            err = "Cannot move - Pressure in {0} is bad.".format(self._tower)
            logger.error(err)
            raise BadN2Pressure(err)
        super().check_status(*args, **kwargs)

    def mv(self, position, *args, **kwargs):
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

        wait : bool, optional
            Wait for the motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.

        ret_status : bool, optional
            Return the status object of the move.

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

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        status : MoveStatus        
            Status object for the move.
        """
        try:
            return super().mv(position, *args, **kwargs)
        # Catch a bad pressure setting.
        except BadN2Pressure:
            logger.warning("Cannot move - pressure in tower {0} is bad.".format(
                self._tower))
            
            
class LinearAero(AeroBase):
    """
    Class for the aerotech linear stage.
    """
    pass


class InterLinearAero(InterlockedAero, LinearAero):
    """
    Class for the interlocked aerotech linear stage.
    """
    pass


class RotationAero(AeroBase):
    """
    Class for the aerotech rotation stage.
    """
    pass


class InterRotationAero(InterlockedAero, RotationAero):
    """
    Class for the interlocked aerotech rotation stage.
    """
    pass

    
class DiodeAero(AeroBase):
    """
    VT50 Micronix Motor of the diodes
    """
    pass
