"""
Script for abstract motor classes used in the SnD.
"""
import logging

from ophyd.device import Component as Cmp
from ophyd.signal import Signal
from ophyd.utils import LimitError
from pcdsdevices.epics_motor import PCDSMotorBase
from pcdsdevices.mv_interface import FltMvInterface

from .snddevice import SndDevice

logger = logging.getLogger(__name__)


class SndMotor(FltMvInterface, SndDevice):
    """
    Base Sndmotor class that has methods common to all the various motors,
    even
    the non-EpicsMotor ones.
    """
    pass


class SndEpicsMotor(PCDSMotorBase, SndMotor):
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
