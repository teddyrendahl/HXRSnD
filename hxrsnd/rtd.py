#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
