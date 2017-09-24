#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

########
# SLAC #
########
from pcdsdevices.device import Device

##########
# Module #
##########
from .utils import get_logger

logger = get_logger(__name__)


class RTDBase(Device):
    """
    Base class for the RTD.
    """
    pass


class OmegaRTD(RTDBase):
    """
    Class for the Omega RTD.
    """
    pass
