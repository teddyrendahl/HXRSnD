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
from pcdsdevices.sim.pv import  using_fake_epics_pv

##########
# Module #
##########
from .conftest import get_classes_in_module
from hxrsnd import aerotech
from hxrsnd.aerotech import (AeroBase, MotorDisabled, MotorFaulted)

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(aerotech, Device))
def test_aerotech_devices_instantiate_and_run_ophyd_functions(dev):
    motor = dev("TEST")
    assert(isinstance(motor.read(), OrderedDict))
    assert(isinstance(motor.describe(), OrderedDict))
    assert(isinstance(motor.describe_configuration(), OrderedDict))
    assert(isinstance(motor.read_configuration(), OrderedDict))

@using_fake_epics_pv
def test_AeroBase_raises_MotorDisabled_if_moved_while_disabled():
    motor = AeroBase("TEST")
    motor.disable()
    with pytest.raises(MotorDisabled):
        motor.move(10)

@using_fake_epics_pv
def test_AeroBase_raises_MotorFaulted_if_moved_while_faulted():
    motor = AeroBase("TEST")
    motor.enable()
    time.sleep(.1)
    motor.axis_fault._read_pv._value = 1
    with pytest.raises(MotorFaulted):
        motor.move(10)
        
