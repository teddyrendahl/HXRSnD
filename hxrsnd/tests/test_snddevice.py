#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import logging
from collections import OrderedDict

import numpy as np
from ophyd.device import Device
from ophyd.tests.conftest import using_fake_epics_pv

from .conftest import get_classes_in_module, fake_device
from hxrsnd import snddevice

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(snddevice, Device))
def test_sndevice_devices_instantiate_and_run_ophyd_functions(dev):
    device = fake_device(dev)
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))
