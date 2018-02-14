"""
Script for abstract motor classes used in the SnD.
"""
import logging

from ophyd.device import Component as Cmp
from ophyd.utils import LimitError

from pcdsdevices.signal import Signal
from pcdsdevices.epics.epicsmotor import EpicsMotor

from .snddevice import SndDevice

logger = logging.getLogger(__name__)


class SndMotor(SndDevice):
    """
    Base Sndmotor class that has methods common to all the various motors, even
    the non-EpicsMotor ones. 

    Note: Remove all the spec methods once pswalker has been updated to use
    latest pcdsdevices and simply inherit from
        `pcdsdevices.mv_interface.FltMvInterface`
    """
    def wm(self):
        """
        Returns the current position of the motor.

        Returns
        -------
        position : float
            Current readback position of the motor.
        """
        return self.position    

    def move_rel(self, rel_position, *args, **kwargs):
        """
        Move relative to the current position, optionally waiting for motion to
        complete. Alias for self.move(self.position + rel_position).

        Parameters
        ----------
        rel_position
            Relative position to move to

        wait : bool, optional
            Wait for the motor to complete the motion.

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

    def mv(self, position, *args, **kwargs):
        """
        Move to a specified position, optionally waiting for motion to
        complete. 

        Parameters
        ----------
        position
            Position to move to.

        wait : bool, optional
            Wait for the motor to complete the motion.

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
        """
        return self.move(position, *args, **kwargs)

    def mvr(self, rel_position, *args, **kwargs):
        """
        Move relative to the current position, optionally waiting for motion to
        complete. Alias for self.mv(self.position + rel_position).

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
        return self.mv(rel_position + self.position, *args, **kwargs)

    def __call__(self, position, *args, **kwargs):
        """
        Moves the motor to the inputted position. Alias for self.mv(position).

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
        return self.mv(position, *args, **kwargs)


class SndEpicsMotor(EpicsMotor, SndMotor):
    """
    SnD motor that inherits from EpicsMotor, therefore having all the relevant 
    signals
    """
    direction_of_travel = Cmp(Signal)


class SamMotor(SndMotor):
    offset_freeze_switch = Cmp(Signal)
    home_forward = Cmp(Signal)
    home_reverse = Cmp(Signal)

    def check_value(self, value, retries=5):
        """
        Check if the value is within the soft limits of the motor.

        Raises
        ------
        ValueError
        """
        if value is None:
            raise ValueError('Cannot write None to epics PVs')
            
        for i in range(retries):
            try:
                low_limit, high_limit = self.limits
                if not (low_limit <= value <= high_limit):
                    raise LimitError("Value {} outside of range: [{}, {}]"
                                     .format(value, low_limit, high_limit))
                return
            except TypeError:
                logger.warning("Failed to get limits, retrying...")
                if i == retries-1:
                    raise
