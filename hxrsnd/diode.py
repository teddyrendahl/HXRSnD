"""
Diodes
"""
import logging

import numpy as np
from ophyd import EpicsSignalRO
from ophyd.device import Component as C, FormattedComponent as FC
from pcdsdevices.areadetector.detectors import DefaultAreaDetector

from .snddevice import SndDevice
from .aerotech import DiodeAero

logger = logging.getLogger(__name__)


class DiodeBase(SndDevice):
    """
    Base class for the diode.
    """
    pass 


class HamamatsuDiode(DiodeBase):
    """
    Class for the Hamamatsu diode.
    """
    pass


class HamamatsuXMotionDiode(SndDevice):
    """
    Class for the Hamamatsu diode but with an X motor
    """
    diode = C(HamamatsuDiode, ":DIODE")
    x = C(DiodeAero, ":X")
    def __init__(self, prefix, name=None, block_pos=5, unblock_pos=0, *args, 
                 block_atol=0.001, desc=None, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.block_pos = block_pos
        self.unblock_pos = unblock_pos
        self.block_atol = block_atol
        self.desc = desc or self.name

    @property
    def blocked(self):
        """
        Returns if the diode is in the blocked position.
        """
        if np.isclose(self.x.position, self.block_pos, atol=self.block_atol):
            return True
        elif np.isclose(self.x.position, self.unblock_pos, 
                        atol=self.block_atol):
            return False
        else:
            return "Unknown"            
        
    def block(self, *args, **kwargs):
        """
        Moves the diode into the blocking position.

        Parameters
        ----------
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
        return self.x.mv(self.block_pos, *args, **kwargs)

    def unblock(self, *args, **kwargs):
        """
        Moves the diode into the nonblocking position.

        Parameters
        ----------
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
        return self.x.mv(self.unblock_pos, *args, **kwargs)


class HamamatsuXYMotionCamDiode(SndDevice):
    """
    Class for the Hamamatsu diode but with X and Y motors
    """
    diode = C(HamamatsuDiode, ":DIODE")
    x = C(DiodeAero, ":X")
    y = C(DiodeAero, ":Y")
    cam = C(DefaultAreaDetector, ":CAM")

    def __init__(self, prefix, name=None, block_pos=5, pos_func=None, 
                 block_atol=0.001, desc=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.block_pos = block_pos
        self.pos_func = pos_func
        self.block_atol = block_atol
        self.desc = desc or self.name

    @property
    def blocked(self):
        """
        Returns if the diode is in the blocked position.

        Returns
        -------
        blocked : bool or str
            True or False if it is close to the blocked or unblocked positions.
            Returns 'Unknown' if it is far from either of those positions.
        """
        if callable(self.pos_func):
            if np.isclose(self.x.position, self.pos_func()+self.block_pos, 
                          atol=self.block_atol):
                return True
            elif np.isclose(self.x.position, self.pos_func(), 
                            atol=self.block_atol):
                return False
        return "Unknown"

    def block(self, *args, **kwargs):
        """
        Moves the diode by the blocking position defined by the position
        function plus the block position.        

        Parameters
        ----------
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
        # Move to the blocked position if we aren't already there
        if self.blocked is True:
            # We are already in the blocked position
            logger.info("Motor '{0}' is currently in the blocked position"
                        "".format(self.x.desc))
        else:
            return self.x.mv(self.pos_func() + self.block_pos, *args, **kwargs)

    def unblock(self, *args, **kwargs):
        """
        Moves the diode by the nonblocking position defined by the position
        function

        Parameters
        ----------
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
        # Move to the blocked position if we aren't already there
        if self.blocked is False:
            # We are already in the blocked position
            logger.info("Motor '{0}' is currently in the unblocked position"
                        "".format(self.x.desc))
        else:
            return self.x.mv(self.pos_func(), *args, **kwargs)


class DiodeIO(SndDevice):
    """
    Peak information for a Wave8 input

    Parameters
    ----------
    prefix : str
        Base name of device

    channel : int
        Channel number of device

    name : str
        Name of Wave8 device
    """
    peakA = FC(EpicsSignalRO,'{self.prefix}:_peakA_{self.channel}')
    peakT = FC(EpicsSignalRO,'{self.prefix}:_peakT_{self.channel}')

    def __init__(self, prefix, channel, name, *,
                 read_attrs=None, **kwargs):
        #Store the channel
        self.channel = channel
        #Default read attributes
        if read_attrs is None:
            read_attrs = ['peakT']
        #Initialize device
        super().__init__(prefix, name=name, read_attrs=read_attrs, **kwargs)


class Wave8(SndDevice):
    """
    Wave8 Device

    A system of sixteen diodes, each with two peaks; A and T.
    """
    diode_0  = C(DiodeIO, '', channel=0,  name='Diode 0')
    diode_1  = C(DiodeIO, '', channel=1,  name='Diode 1')
    diode_2  = C(DiodeIO, '', channel=2,  name='Diode 2')
    diode_3  = C(DiodeIO, '', channel=3,  name='Diode 3')
    diode_4  = C(DiodeIO, '', channel=4,  name='Diode 4')
    diode_5  = C(DiodeIO, '', channel=5,  name='Diode 5')
    diode_6  = C(DiodeIO, '', channel=6,  name='Diode 6')
    diode_7  = C(DiodeIO, '', channel=7,  name='Diode 7')
    diode_8  = C(DiodeIO, '', channel=8,  name='Diode 8')
    diode_9  = C(DiodeIO, '', channel=9,  name='Diode 9')
    diode_10 = C(DiodeIO, '', channel=10, name='Diode 10')
    diode_11 = C(DiodeIO, '', channel=11, name='Diode 11')
    diode_12 = C(DiodeIO, '', channel=12, name='Diode 12')
    diode_13 = C(DiodeIO, '', channel=13, name='Diode 13')
    diode_14 = C(DiodeIO, '', channel=14, name='Diode 14')
    diode_15 = C(DiodeIO, '', channel=15, name='Diode 15')
