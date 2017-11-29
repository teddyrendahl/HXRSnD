"""
RTDs
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
from ophyd import Component
from ophyd.status import wait as status_wait

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.epics.signal import EpicsSignal, EpicsSignalRO

##########
# Module #
##########


class SeqBase(Device):
    """
    Base sequencer class.
    """
    state_control = Component(EpicsSignal, ":PLYCTL")

    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc = desc
        super().__init__(prefix, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name    
    
    def start(self):
        """
        Start the sequencer.
        """
        status = self.state_control.set(1)
        status_wait(status)
        
    def stop(self):
        """
        Stop the sequencer.
        """
        status = self.state_control.set(0)
        status_wait(status)        
