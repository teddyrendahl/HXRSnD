"""
Script to hold the split and delay class.

All units of time are in picoseconds, units of length are in mm.
"""
import os
import logging

from ophyd import Component as Cmp

from .snddevice import SndDevice
from .pneumatic import SndPneumatics
from .utils import absolute_submodule_path
from .tower import DelayTower, ChannelCutTower
from .diode import HamamatsuXMotionDiode, HamamatsuXYMotionCamDiode
from .macromotor import Energy1Macro, Energy1CCMacro, Energy2Macro, DelayMacro

logger = logging.getLogger(__name__)


class SplitAndDelay(SndDevice):
    """
    Hard X-Ray Split and Delay System.

    Components

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
    t1 = Cmp(DelayTower, ":T1", pos_inserted=21.1, pos_removed=0, 
                   desc="Tower 1")
    t4 = Cmp(DelayTower, ":T4", pos_inserted=21.1, pos_removed=0, 
                   desc="Tower 4")

    # Channel Cut Towers
    t2 = Cmp(ChannelCutTower, ":T2", pos_inserted=None, pos_removed=0, 
             desc="Tower 2")
    t3 = Cmp(ChannelCutTower, ":T3", pos_inserted=None, pos_removed=0, 
             desc="Tower 3")

    # Pneumatic Air Bearings
    ab = Cmp(SndPneumatics, "")

    # SnD and Delay line diagnostics
    di = Cmp(HamamatsuXMotionDiode, ":DIA:DI", desc="DI")
    dd = Cmp(HamamatsuXYMotionCamDiode, ":DIA:DD", desc="DD")
    do = Cmp(HamamatsuXMotionDiode, ":DIA:DO", desc="DO")

    # Channel Cut Diagnostics
    dci = Cmp(HamamatsuXMotionDiode, ":DIA:DCI", block_pos=-5, desc="DCI")
    dcc = Cmp(HamamatsuXYMotionCamDiode, ":DIA:DCC", block_pos=-5, desc="DCC")
    dco = Cmp(HamamatsuXMotionDiode, ":DIA:DCO",  block_pos=-5, desc="DCO")

    # Macro motors
    E1 = Cmp(Energy1Macro, "", desc="Delay Energy")
    E1_cc = Cmp(Energy1CCMacro, "", desc="CC Delay Energy")
    E2 = Cmp(Energy2Macro, "", desc="CC Energy")
    delay = Cmp(DelayMacro, "", desc="Delay")
    
    def __init__(self, prefix, name=None, daq=None, RE=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.daq = daq
        self.RE = RE
        self._delay_towers = [self.t1, self.t4]
        self._channelcut_towers = [self.t2, self.t3]
        self._towers = self._delay_towers + self._channelcut_towers
        self._delay_diagnostics = [self.di, self.dd, self.do]
        self._channelcut_diagnostics = [self.dci, self.dcc, self.dco]
        self._diagnostics = self._delay_diagnostics+self._channelcut_diagnostics

        # Set the position calculators of dd and dcc
        self.dd.pos_func = lambda : \
          self.E1._get_delay_diagnostic_position()
        self.dcc.pos_func = lambda : \
          self.E2._get_channelcut_diagnostic_position()
          
    def diag_status(self):
        """
        Prints a string containing the blocking status and the position of the
        motor.
        """
        status = "\n{0}{1:<14}|{2:^16}|{3:^16}\n{4}{5}".format(
            " "*2, "Diagnostic", "Blocking", "Position", " "*2, "-"*50)
        for diag in self._diagnostics:
            status += "\n{0}{1:<14}|{2:^16}|{3:^16.3f}".format(
                " "*2, diag.desc, str(diag.blocked), diag.x.position)
        logger.info(status)

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

    def main_screen(self, print_msg=True):
        """
        Launches the main SnD screen.
        """
        # Get the absolute path to the screen
        path = absolute_submodule_path("hxrsnd/screens/snd_main")
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
