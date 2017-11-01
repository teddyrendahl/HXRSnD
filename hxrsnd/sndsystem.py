"""
Script to hold the split and delay class.

All units of time are in picoseconds, units of length are in mm.
"""
############
# Standard #
############
import os
import logging

###############
# Third Party #
###############
import numpy as np
from ophyd import Component
from ophyd.status import wait as status_wait
from ophyd.utils.epics_pvs import raise_if_disconnected
from bluesky import RunEngine

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.daq import Daq, make_daq_run_engine

##########
# Module #
##########
from .state import OphydMachine
from .pneumatic import SndPneumatics
from .utils import flatten
from .bragg import bragg_angle, cosd, sind
from .tower import DelayTower, ChannelCutTower
from .diode import HamamatsuXMotionDiode, HamamatsuXYMotionCamDiode
from .macromotor import Energy1Macro, Energy2Macro, DelayMacro

logger = logging.getLogger(__name__)


class SplitAndDelay(Device):
    """
    Hard X-Ray Split and Delay System.

    Components
    ----------
    t1 : DelayTower
        Tower 1 in the split and delay system.

    t4 : DelayTower
        Tower 4 in the split and delay system.

    t2 : ChannelCutTower
        Tower 2 in the split and delay system.

    t3 : ChannelCutTower
        Tower 3 in the split and delay system.

    ab : SndPneumatics
        Vacuum device object for the system.

    di : HamamatsuXYMotionCamDiode
        Input diode for the system.
    
    dd : HamamatsuXYMotionCamDiode
        Diode between the two delay towers.

    do : HamamatsuXYMotionCamDiode
        Output diode for the system.

    dci : HamamatsuXMotionDiode
        Input diode for the channel cut line.
    
    dcc : HamamatsuXMotionDiode
        Diode between the two channel cut towers.
    
    dco : HamamatsuXMotionDiode
        Input diode for the channel cut line.

    E1 : Energy1Macro
        Delay energy pseudomotor.

    E2 : Energy2Macro
        Channel cut energy pseudomotor.

    delay : DelayMacro
        Delay pseudomotor.
    """
    # Delay Towers
    t1 = Component(DelayTower, ":T1", y1="A:ACT0", y2="A:ACT1",
                   chi1="A:ACT2", chi2="B:ACT0", dh="B:ACT1",
                   pos_inserted=21.1, pos_removed=0, desc="Tower 1")
    t4 = Component(DelayTower, ":T4", y1="C:ACT0", y2="C:ACT1",
                   chi1="C:ACT2", chi2="D:ACT0", dh="D:ACT1",
                   pos_inserted=21.1, pos_removed=0, desc="Tower 4")

    # Channel Cut Towers
    t2 = Component(ChannelCutTower, ":T2", pos_inserted=None, 
                   pos_removed=0, desc="Tower 2")
    t3 = Component(ChannelCutTower, ":T3", pos_inserted=None, 
                   pos_removed=0, desc="Tower 3")

    # Pneumatic Air Bearings
    ab = Component(SndPneumatics, "")

    # SnD and Delay line diagnostics
    di = Component(HamamatsuXMotionDiode, ":DIA:DI")
    dd = Component(HamamatsuXYMotionCamDiode, ":DIA:DD")
    do = Component(HamamatsuXMotionDiode, ":DIA:DO")

    # Channel Cut Diagnostics
    dci = Component(HamamatsuXMotionDiode, ":DIA:DCI")
    dcc = Component(HamamatsuXYMotionCamDiode, ":DIA:DCC")
    dco = Component(HamamatsuXMotionDiode, ":DIA:DCO")

    # Macro motors
    E1 = Component(Energy1Macro, "", desc="Delay Energy")
    E2 = Component(Energy2Macro, "", desc="CC Energy")
    delay = Component(DelayMacro, "", desc="Delay")

    # DAQ
    daq = Component(Daq, None, platform=1)
    
    def __init__(self, prefix, desc=None, RE=None, *args, **kwargs):
        self.desc = desc
        super().__init__(prefix, *args, **kwargs)
        self._delay_towers = [self.t1, self.t4]
        self._channelcut_towers = [self.t2, self.t3]
        self._towers = self._delay_towers + self._channelcut_towers
        self._delay_diagnostics = [self.di, self.dd, self.do]
        self._channelcut_diagnostics = [self.dci, self.dcc, self.dco]
        self._diagnostics = self._delay_diagnostics+self._channelcut_diagnostics        
        
        # Get the LCLS RunEngine
        self.RE = make_daq_run_engine(self.daq)

        if self.desc is None:
            self.desc = self.name    

    @property
    def theta1(self):
        """
        Returns the bragg angle the the delay line is currently set to
        maximize.

        Returns
        -------
        theta1 : float
            The bragg angle the delay line is currently set to maximize 
            in degrees.
        """
        return self.t1.theta

    @property
    def theta2(self):
        """
        Returns the bragg angle the the delay line is currently set to
        maximize.

        Returns
        -------
        theta2 : float
            The bragg angle the channel cut line is currently set to maximize 
            in degrees.
        """
        return self.t2.theta    

    def main_screen(self):
        """
        Launches the main SnD screen.
        """
        # Get the absolute path to the screen
        path = absolute_submodule_path("HXRSnD/screens/snd_main")
        if print_msg:
            logger.info("Launching expert screen.")
        os.system("{0} {1} {2} &".format(path, p, axis))
        
    def status(self, print_status=True):
        """
        Returns the status of the split and delay system.
        
        Returns
        -------
        Status : str            
        """
        status =  "Split and Delay System Status\n"
        status += "-----------------------------"
        status = self.E1.status(status, 0, print_status=False)
        status = self.E2.status(status, 0, print_status=False)
        status = self.delay.status(status, 0, print_status=False, newline=True)
        status = self.t1.status(status, 0, print_status=False, newline=True)
        status = self.t2.status(status, 0, print_status=False, newline=True)
        status = self.t3.status(status, 0, print_status=False, newline=True)
        status = self.t4.status(status, 0, print_status=False, newline=True)
        status = self.ab.status(status, 0, print_status=False, newline=False)

        if print_status:
            logger.info(status)
        else:
            logger.debug(status)
            return status

    def __repr__(self):
        """
        Returns the status of the device. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)
