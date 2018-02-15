"""
RTDs
"""
import logging

from ophyd import Component
from ophyd.status import wait as status_wait

from pcdsdevices.device import Device
from pcdsdevices.epics.signal import EpicsSignal, EpicsSignalRO

logger = logging.getLogger(__name__)


class SeqBase(Device):
    """
    Base sequencer class.
    """
    state_control = Component(EpicsSignal, ":PLYCTL")

    def __init__(self, prefix, name=None, desc=None, timeout=2, *args, 
                 **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)
    
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
