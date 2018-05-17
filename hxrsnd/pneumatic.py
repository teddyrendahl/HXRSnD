"""
Pneumatics for SnD
"""
import logging

from ophyd import Component as Cmp
from ophyd.signal import EpicsSignal, EpicsSignalRO

from .snddevice import SndDevice

logger = logging.getLogger(__name__)


class PneuBase(SndDevice):
    """
    Base class for the penumatics.
    """    
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
        status += "{0}{1:<16}|{2:^16}\n".format(" "*offset, self.desc+"", 
                                                self.position)
        if newline:
            status += "\n"
        if print_status is True:
            logger.info(status)
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
    valve = Cmp(EpicsSignal, ":VGP")

    def open(self):
        """
        Closes the valve.
        """
        if self.opened:
            logger.info("Valve currently open.")
        else:
            return self.valve.set(1, timeout=self.set_timeout)
    
    def close(self):
        """
        Closes the valve.
        """
        if self.closed:
            logger.info("Valve currently closed.")
        else:
            return self.valve.set(0, timeout=self.set_timeout)
        
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
        else:
            return "UNKNOWN"

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
    pressure = Cmp(EpicsSignalRO, ":GPS")
        
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
        if self.pressure.value == 0:
            return "GOOD"
        elif self.pressure.value == 1:
            return "BAD"
        else:
            return "UNKNOWN"

    @property
    def good(self):
        """
        Returns if the pressure is in the 'good' state.

        Returns
        -------
        good : bool
            True if the pressure switch is in the 'good' state.
        """
        return (self.position == "GOOD")

    @property
    def bad(self):
        """
        Returns if the pressure is in the 'bad' state.

        Returns
        -------
        bad : bool
            True if the pressure switch is in the 'bad' state.
        """
        return (self.position == "BAD")


class SndPneumatics(SndDevice):
    """
    Class that contains the various pneumatic components of the system.

    Components
    ----------
    t1_valve : ProportionalValve
        Proportional valve on T1.

    t4_valve : ProportionalValve
        Proportional valve on T4.

    vac_valve : ProportionalValve
        Proportional valve on the overall system.

    t1_pressure : PressureSwitch
        Pressure switch on T1.

    t4_pressure : PressureSwitch
        Pressure switch on T4.

    vac_pressure : PressureSwitch
        Pressure switch on the overall system.
    """
    t1_valve = Cmp(ProportionalValve, ":N2:T1", desc="T1 Valve")
    t4_valve = Cmp(ProportionalValve, ":N2:T4", desc="T4 Valve")
    vac_valve = Cmp(ProportionalValve, ":VAC", desc="Vacuum Valve")

    t1_pressure = Cmp(PressureSwitch, ":N2:T1", desc="T1 Pressure")
    t4_pressure = Cmp(PressureSwitch, ":N2:T4", desc="T4 Pressure")
    vac_pressure = Cmp(PressureSwitch, ":VAC", desc="Vacuum Pressure")

    def __init__(self, prefix, name=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self._valves = [self.t1_valve, self.t4_valve, self.vac_valve]
        self._pressure_switches = [self.t1_pressure, self.t4_pressure,
                                   self.vac_pressure]

    def status(self, status="", offset=0, print_status=True, newline=False):
        """
        Returns the status of the vacuum system.

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
        status += "\n{0}Pneumatics".format(" "*offset)
        status += "\n{0}{1}\n{0}{2:^16}|{3:^16}\n{0}{4}\n".format(
            " "*(offset+2), "-"*34, "Device", "State", "-"*34)
        for valve in self._valves:
            status += valve.status(offset=offset+2, print_status=False)
        for pressure in self._pressure_switches:
            status += pressure.status(offset=offset+2, print_status=False)
                    
        if newline:
            status += "\n"
        if print_status is True:
            logger.info(status)
        else:
            return status

    def open(self):
        """
        Opens all the valves in the vacuum system.
        """
        logging.info("Opening valves in SnD system.")
        for valve in self._valves:
            valve.open()

    def close(self):
        """
        Opens all the valves in the vacuum system.
        """
        logging.info("Closing valves in SnD system.")
        for valve in self._valves:
            valve.close()

    @property
    def valves(self):
        """
        Prints the positions of all the valves in the system.
        """
        status = ""
        for valve in self._valves:
            status += valve.status(print_status=False)
        logger.info(status)

    @property
    def pressures(self):
        """
        Prints the pressures of all the pressure switches in the system.
        """
        status = ""
        for pressure in self._pressure_switches:
            status += pressure.status(print_status=False)
        logger.info(status)

    def __repr__(self):
        """
        Returns the status of the device. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)
