#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pneumatics for SnD
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import numpy as np

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.component import Component
from pcdsdevices.epics.signal import EpicsSignal, EpicsSignalRO

logger = logging.getLogger(__name__)

class PneuBase(Device):
    """
    Base class for the penumatics.
    """

    def __init__(self, prefix, desc=None, *args, **kwargs):
        self.desc=desc
        super().__init__(prefix, *args, **kwargs)
        if desc is None:
            self.desc = self.name    
    
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
        status += "{0}{1}: {3}\n".format(" "*offset, self.desc, self.position)
        if newline:
            status += "\n"
        if print_status is True:
            print(status)
        else:
            return status

    def __repr__(self):
        """
        Returns the status of the valve. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)


class ProportionalValve(PneuBase):
    """
    Class for the proportional pneumatic valves.

    Components
    ----------
    valve : EpicsSignal
        Valve control and readback pv.
    """
    valve = Component(EpicsSignal, ":VGP")

    def open(self):
        """
        Closes the valve.
        """
        if self.opened:
            logger.info("Valve currently open.")
        else:
            self.valve.put(1)
    
    def close(self):
        """
        Closes the valve.
        """
        if self.closed:
            logger.info("Valve currently closed.")
        else:
            self.valve.put(0)
        
    @property
    def position(self):
        """
        Returns the position of the valve.

        Returns
        -------
        position : str
            String saying the current position of the valve. Can be "OPEN" or
            "CLOSED". 
        """
        if self.valve.value == 1:
            return "OPEN"
        elif self.valve.value == 0:
            return "CLOSED"

    @property
    def opened(self):
        """
        Returns if the valve is in the opened state.

        Returns
        -------
        opened : bool
            True if the valve is currently in the 'opened' position.
        """
        return (self.position == "OPEN")

    @property
    def closed(self):
        """
        Returns if the valve is in the closed state.

        Returns
        -------
        closed : bool
            True if the valve is currently in the 'closed' position.
        """
        return (self.position == "CLOSED")
    

class PressureSwitch(PneuBase):
    """
    Pressure switch.

    Components
    ----------
    pressure : EpicsSignalRO
        Pressure readbac signal.
    """
    pressure = Component(EpicsSignalRO, ":GPS")
        
    @property
    def position(self):
        """
        Returns the position of the valve.

        Returns
        -------
        position : str
            String saying the current position of the valve. Can be "OPEN" or
            "CLOSED". 
        """
        if self.valve.value ==0:
            return "GOOD"
        elif self.valve.value == 1:
            return "BAD"

    @property
    def good(self):
        """
        Returns if the pressure is in the 'good' state.

        Returns
        -------
        good : bool
            True if the pressure switch is in the 'good' state.
        """
        return (self.position == "OPEN")

    @property
    def bad(self):
        """
        Returns if the pressure is in the 'bad' state.

        Returns
        -------
        bad : bool
            True if the pressure switch is in the 'bad' state.
        """
        return (self.position == "OPEN")

    
