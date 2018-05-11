"""
Sequencer Class
"""
import logging

from ophyd import Component as Cmp
from ophyd.signal import EpicsSignal
from ophyd.status import wait as status_wait

from .snddevice import SndDevice

logger = logging.getLogger(__name__)


class SeqBase(SndDevice):
    """
    Base sequencer class.
    """
    state_control = Cmp(EpicsSignal, ":PLYCTL")
    
    def start(self):
        """
        Start the sequencer.
        """
        status = self.state_control.set(1, timeout=self.timeout)
        status_wait(status)
        
    def stop(self):
        """
        Stop the sequencer.
        """
        status = self.state_control.set(0, timeout=self.timeout)
        status_wait(status)        
