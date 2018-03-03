#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import pytest
from ophyd.device import Device
from ophyd.tests.conftest import using_fake_epics_pv

from .conftest import get_classes_in_module, fake_device
from hxrsnd import macromotor

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(macromotor, Device))
def test_devices_instantiate_and_run_ophyd_functions(dev):
    device = fake_device(dev)
    assert(isinstance(device.read(), dict))
    assert(isinstance(device.describe(), dict))
    assert(isinstance(device.describe_configuration(), dict))
    assert(isinstance(device.read_configuration(), dict))
