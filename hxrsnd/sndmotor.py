import logging
import ophyd.epics_motor
from pcdsdevices.epics.epicsmotor import EpicsMotor
from ophyd.device import Component
from pcdsdevices.device import Device
from pcdsdevices.signal import Signal
from pcdsdevices.sim.signal import FakeSignal
from ophyd.utils import LimitError

logger = logging.getLogger(__name__)

class SndMotor(EpicsMotor, Device):
    """
    Base Sndmotor class
    """
    def __init__(self, prefix, name=None, desc=None, *args, **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name


class SamMotor(SndMotor):
    offset_freeze_switch = Component(FakeSignal)
    direction_of_travel = Component(FakeSignal)
    home_forward = Component(FakeSignal)
    home_reverse = Component(FakeSignal)


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
