#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time
from collections import OrderedDict
import pytest

import numpy as np
from ophyd.tests.conftest import using_fake_epics_pv
from ophyd.device import Device

from hxrsnd import detectors
from .conftest import get_classes_in_module, fake_detector

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(detectors, Device))
def test_rtd_devices_instantiate_and_run_ophyd_functions(dev):
    device = fake_detector(dev)
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))
