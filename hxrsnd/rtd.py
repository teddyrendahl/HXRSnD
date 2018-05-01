"""
RTDs
"""
import logging

from .snddevice import SndDevice

logger = logging.getLogger(__name__)


class RTDBase(SndDevice):
    """
    Base class for the RTD.
    """
    pass


class OmegaRTD(RTDBase):
    """
    Class for the Omega RTD.
    """
    pass
