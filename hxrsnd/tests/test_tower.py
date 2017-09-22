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
from hxrsnd import tower
from hxrsnd.sndsystem import DelayTower, ChannelCutTower
from hxrsnd.exceptions import MotorDisabled, MotorFaulted

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(tower, Device))
def test_devices_instantiate_and_run_ophyd_functions(dev):
    device = dev("TEST")
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))

@using_fake_epics_pv
def test_DelayTower_does_not_move_if_motors_not_ready():
    tower = DelayTower("TEST")
    tower.disable()
    time.sleep(.5)
    tower.tth.limits = (-100, 100)
    tower.th1.limits = (-100, 100)
    tower.th2.limits = (-100, 100)

    tower.tth.user_setpoint.check_value = lambda x: None
    tower.th1.user_setpoint.check_value = lambda x: None
    tower.th2.user_setpoint.check_value = lambda x: None    

    with pytest.raises(MotorDisabled):
        tower.energy = 10
    tower.enable()
    tower.tth.axis_fault._read_pv._value = True
    with pytest.raises(MotorFaulted):
        tower.energy = 10

@using_fake_epics_pv
def test_ChannelCutTower_does_not_move_if_motors_not_ready():
    tower = ChannelCutTower("TEST")
    tower.disable()
    time.sleep(.5)
    tower.th.limits = (-100, 100)
    tower.th.user_setpoint.check_value = lambda x: None

    with pytest.raises(MotorDisabled):
        tower.energy = 10
    tower.enable()
    tower.th.axis_fault._read_pv._value = True
    with pytest.raises(MotorFaulted):
        tower.energy = 10
