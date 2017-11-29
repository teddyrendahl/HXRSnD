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

logger = logging.getLogger(__name__)


class RTDBase(Device):
    """
    Base class for the RTD.
    """
    def __init__(self, prefix, name=None, desc=None, *args, **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name        


class OmegaRTD(RTDBase):
    """
    Class for the Omega RTD.
    """
    pass
