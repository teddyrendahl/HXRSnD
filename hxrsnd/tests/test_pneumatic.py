#!/usr/bin/env python
# -*- coding: utf-8 -*-
############
# Standard #
############
import logging
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
from hxrsnd import pneumatic
from hxrsnd.pneumatic import ProportionalValve, PressureSwitch, SndPneumatics
from .conftest import get_classes_in_module

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(pneumatic, Device))
def test_devices_instantiate_and_run_ophyd_functions(dev):
    device = dev("TEST")
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))

@using_fake_epics_pv
def test_ProportionalValve_opens_and_closes_correctly():
    valve = ProportionalValve("TEST")
    valve.open()
    assert valve.position == "OPEN"
    assert valve.opened is True
    assert valve.closed is False
    valve.close()
    assert valve.position == "CLOSED"
    assert valve.opened is False
    assert valve.closed is True

@using_fake_epics_pv
def test_PressureSwitch_reads_correctly():
    press = PressureSwitch("TEST")
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
    vac = SndPneumatics("TEST")
    for valve in vac._valves:
        valve.close()
    vac.open()
    for valve in vac._valves:
        assert valve.opened
    vac.close()
    for valve in vac._valves:
        assert valve.closed
