#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTDs
"""
import logging

from pcdsdevices.device import Device

logger = logging.getLogger(__name__)


class RTDBase(Device):
    """
    Base class for the RTD.
    """
    def __init__(self, prefix, name=None, desc=None, *args, **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)


class OmegaRTD(RTDBase):
    """
    Class for the Omega RTD.
    """
    pass
