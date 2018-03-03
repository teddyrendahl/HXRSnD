#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import logging
from copy import deepcopy
from collections import OrderedDict

import numpy as np
import pandas as pd
from ophyd.device import Device
from ophyd.sim import SynAxis
from ophyd.tests.conftest import using_fake_epics_pv

from hxrsnd import sndmotor
from .conftest import get_classes_in_module, fake_device
from ..sndmotor import CalibMotor
from ..exceptions import InputError

logger = logging.getLogger(__name__)

@using_fake_epics_pv
@pytest.mark.parametrize("dev", get_classes_in_module(sndmotor, Device))
def test_sndmotor_devices_instantiate_and_run_ophyd_functions(dev):
    device = fake_device(dev)
    assert(isinstance(device.read(), OrderedDict))
    assert(isinstance(device.describe(), OrderedDict))
    assert(isinstance(device.describe_configuration(), OrderedDict))
    assert(isinstance(device.read_configuration(), OrderedDict))

def test_CalibMotor_configure_raises_errors_on_bad_inputs():
    dev = CalibMotor("TST", name="test")
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

@pytest.mark.parametrize("scale", [None, [1]])
@pytest.mark.parametrize("start", [None, [1]])
@pytest.mark.parametrize("scan", [None, pd.DataFrame(columns=['b'])])
def test_CalibMotor_configure_works_with_good_inputs(scale, start, scan):
    dev = CalibMotor("TST", name="test")

    # There should be no errors with this configure
    assert dev.configure(calib=pd.DataFrame(columns=['a']), 
                         motors=[SynAxis(name="test_1")],
                         scan=scan,
                         scale=scale,
                         start=start)

    config = dev.read_configuration()
    # Assert the extra values are in the cofiguration
    assert config['scan']['value'] is scan
    assert config['scale']['value'] == scale
    assert config['start']['value'] == start

@pytest.mark.parametrize("calib", [None, 
                                   pd.DataFrame(columns=['a']), 
                                   pd.DataFrame(columns=['a', 'b'])])
@pytest.mark.parametrize("motors", [None, 
                                    [SynAxis(name='a')],
                                    [SynAxis(name='a'), SynAxis(name='b')]])
def test_CalibMotor_has_calib_correctly_indicates_there_is_a_valid_calibration(
        calib, motors):
    dev = CalibMotor("TST", name="test")
    # Force replace the underlying calibration to use the inputs
    dev._calib['calib']['value'] = calib
    dev._calib['motors']['value'] = motors
    
    # There must be both a calibration and motors, and they are the same length
    expected_logic = bool((calib is not None and motors) and 
                          (len(calib.columns) == len(motors)))
    assert dev.has_calib == expected_logic
        
def test_CalibMotor_calibration_returns_correct_parameters():
    dev = CalibMotor("TST", name="test")
    # Should be none if there is no calibration
    assert dev.calibration is None
    
    # Create the parmeters we will pass
    calib = pd.DataFrame(columns=['a'])
    scan = pd.DataFrame(columns=['b'])
    motors = [SynAxis(name='test')]
    scale = [1]
    start = [0]

    # Configure and test the resulting calibration
    dev.configure(calib=calib, scan=scan, motors=motors, scale=scale,
                  start=start)
    calibration = dev.calibration
    assert calibration['calib'] is calib
    assert calibration['scan'] is scan
    assert calibration['motors'] == [m.name for m in motors]
    assert calibration['scale'] == scale
    assert calibration['start'] == start
    
