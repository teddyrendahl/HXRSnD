#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import pytest
import logging
from collections import OrderedDict

import numpy as np
from ophyd.device import Device
from ophyd.tests.conftest import using_fake_epics_pv

from hxrsnd import pneumatic
from hxrsnd.pneumatic import ProportionalValve, PressureSwitch, SndPneumatics
from .conftest import get_classes_in_module, fake_device

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(pneumatic, Device))
def test_devices_instantiate_and_run_ophyd_functions(dev):
    device = fake_device(dev)
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))

@using_fake_epics_pv
def test_ProportionalValve_opens_and_closes_correctly():
    valve = fake_device(ProportionalValve)
    valve.open()
    time.sleep(.1)
    assert valve.position == "OPEN"
    assert valve.opened is True
    assert valve.closed is False
    valve.close()
    time.sleep(.1)
    assert valve.position == "CLOSED"
    assert valve.opened is False
    assert valve.closed is True

@using_fake_epics_pv
def test_PressureSwitch_reads_correctly():
    press = fake_device(PressureSwitch)
    press.pressure._read_pv._value = 0
    assert press.position == "GOOD"
    assert press.good is True
    assert press.bad is False
    press.pressure._read_pv._value = 1
    assert press.position == "BAD"
    assert press.good is False
    assert press.bad is True    

@using_fake_epics_pv    
def test_SndPneumatics_open_and_close_methods():
    vac = fake_device(SndPneumatics)
    for valve in vac._valves:
        valve.close()
    time.sleep(.1)
    vac.open()
    time.sleep(.1)
    for valve in vac._valves:
        assert valve.opened
    vac.close()
    time.sleep(.1)
    for valve in vac._valves:
        assert valve.closed
