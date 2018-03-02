#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from copy import deepcopy

import pytest
import pandas as pd
from ophyd.device import Device
from ophyd.sim import SynAxis
from ophyd.tests.conftest import using_fake_epics_pv

from .conftest import get_classes_in_module, fake_device
from ..macromotor import CalibMacro
from ..exceptions import InputError
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

def test_CalibMacro_check_calib_raises_errors_properly():
    dev = CalibMacro("TST", name="test")
    config = deepcopy(dev.read_configuration())

    # Define a quick function to test value equivalence
    def test_config_change(cfg1, cfg2): 
        for key1, key2 in zip(cfg1.keys(), cfg2.keys()):
            if cfg1[key1]['value'] != cfg2[key2]['value']:
                return False
        return True

    # No errors if we dont pass any calib or motors
    assert dev.configure()
    assert test_config_change(config, dev.read_configuration())

    # InputError when we pass motors but not a calibration
    with pytest.raises(InputError):
        dev.configure(motors=[SynAxis(name="test")])
    # Assert the calibration wasnt changed
    assert test_config_change(config, dev.read_configuration())

    # TypeError when the calibration is not a dataframe
    with pytest.raises(TypeError):
        dev.configure(calib="test")
    # Assert the calibration wasnt changed
    assert test_config_change(config, dev.read_configuration())

    # InputError if we pass a dataframe but no motors
    with pytest.raises(InputError):
        dev.configure(calib=pd.DataFrame(columns=['a']))
    # Assert the calibration wasnt changed
    assert test_config_change(config, dev.read_configuration())
        
    # InputError if we pass a different number of motors as calib columns
    with pytest.raises(InputError):
        dev.configure(calib=pd.DataFrame(columns=['a', 'b']), 
                      motors=[SynAxis(name="test")])
    # Assert the calibration wasnt changed
    assert test_config_change(config, dev.read_configuration())
    with pytest.raises(InputError):
        dev.configure(calib=pd.DataFrame(columns=['a']), 
                      motors=[SynAxis(name="test_1"), SynAxis(name="test_2")])
    # Assert the calibration wasnt changed
    assert test_config_change(config, dev.read_configuration())

    # No error if we pass both correctly but none of the extra data
    assert dev.configure(calib=pd.DataFrame(columns=['a']), 
                         motors=[SynAxis(name="test_1")])
    # Assert the calibration was changed this time changed
    assert isinstance(dev.read_configuration()['calib']['value'], pd.DataFrame)
    assert isinstance(dev.read_configuration()['motors']['value'], list)
    
# def test_CalibMacro    
