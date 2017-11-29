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
from .conftest import get_classes_in_module, fake_device
from hxrsnd import attocube
from hxrsnd.attocube import (EccBase, MotorDisabled, MotorError)

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(attocube, Device))
def test_attocube_devices_instantiate_and_run_ophyd_functions(dev):
    motor = fake_device(dev)
    assert(isinstance(motor.read(), OrderedDict))
    assert(isinstance(motor.describe(), OrderedDict))
    assert(isinstance(motor.describe_configuration(), OrderedDict))
    assert(isinstance(motor.read_configuration(), OrderedDict))    

@using_fake_epics_pv
def test_EccBase_raises_MotorDisabled_if_moved_while_disabled():
    motor = fake_device(EccBase)
    motor.motor_error._read_pv._value = 0
    assert not motor.error
    motor.disable()
    assert not motor.enabled
    with pytest.raises(MotorDisabled):
        motor.move(10)

@using_fake_epics_pv
def test_EccBase_raises_MotorError_if_moved_while_faulted():
    motor = fake_device(EccBase)
    motor.motor_error._read_pv._value = 0
    assert not motor.error
    motor.enable()
    time.sleep(.5)
    assert motor.enabled
    motor.motor_error._read_pv._value = 1
    with pytest.raises(MotorError):
        motor.move(10)

# @using_fake_epics_pv
# @pytest.mark.parametrize("position", [1])
# def test_EccBase_callable_moves_the_motor(position):
#     motor = EccBase("TEST")
#     motor.enable()
#     motor.limits = (0, 1)
#     assert motor.user_setpoint.value != position
#     time.sleep(0.25)
#     motor(position, wait=False)
#     time.sleep(0.1)
#     assert motor.user_setpoint.value == position
