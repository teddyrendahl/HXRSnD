#!/usr/bin/env python
# -*- coding: utf-8 -*-
############
# Standard #
############
import logging
import time
from collections import OrderedDict
import pytest

###############
# Third Party #
###############
import numpy as np
from ophyd.device import Device

########
# SLAC #
########
from pcdsdevices.sim.pv import using_fake_epics_pv

##########
# Module #
##########
from .conftest import get_classes_in_module
from hxrsnd import macromotor
from hxrsnd.utils import get_logger

logger = get_logger(__name__, log_file=False)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(macromotor, Device))
def test_devices_instantiate_and_run_ophyd_functions(dev):
    device = dev("TEST")
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))
