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
from bluesky.preprocessors  import run_wrapper

from hxrsnd import sndmotor
from .conftest import get_classes_in_module, fake_device, SynCamera
from ..plans.scans import centroid_scan
from ..sndmotor import CalibMotor
from ..exceptions import InputError

logger = logging.getLogger(__name__)
rtol = 1e-6                             # Numpy relative tolerance

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
    assert calibration['calib'].equals(calib)
    assert calibration['scan'].equals(scan)
    assert calibration['motors'] == [m.name for m in motors]
    assert calibration['scale'] == scale
    assert calibration['start'] == start

def test_CalibMotor_calibrates_correctly(fresh_RE, get_calib_motor):
    # Define all the needed variables
    motor = get_calib_motor
    calib_motors = motor.calib_motors
    camera = SynCamera(*motor.calib_motors, motor, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    start, stop, steps = -1, 1, 5
    
    # Perform the calibration
    motor.calibrate(start, stop, steps, RE=fresh_RE, detector=camera,
                    average=1, tolerance=0, confirm_overwrite=False)
    
    # Grab the resulting calibration parameters
    df_calib = motor.calibration['calib']
    df_scan = motor.calibration['scan']
    
    # Expected positions of the centroids are the first positions
    expected_centroids = df_scan[[c.name for c in centroids]].iloc[0]

    for i in range(len(df_scan)):
        # Move to the scan position for the main motor
        motor.set(df_calib[motor.motor_fields[0]].iloc[i])

        for cmotor, exp_cent, cent in zip(calib_motors, expected_centroids, 
                                          centroids):
            # Move to the abosolute corrected position
            cmotor.set(df_calib[cmotor.name+"_post"].iloc[i])
            # Check the centroids are where they should be
            assert np.isclose(cent.get(), exp_cent, rtol=rtol)

def test_CalibMotor_move_compensation(fresh_RE, get_calib_motor):
    # Define all the needed variables
    motor = get_calib_motor
    calib_motors = motor.calib_motors
    camera = SynCamera(*motor.calib_motors, motor, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    start, stop, steps = -1, 1, 5

    # Create the plan
    def test_plan():
        # Perform the calibration
        df_scan = (yield from centroid_scan(
            camera,
            motor,
            start, stop, steps,
            motor_fields=motor.motor_fields,
            detector_fields=motor.detector_fields))
    
        # Expected positions of the centroids are the first positions
        df_centroids = df_scan[[c.name for c in centroids]]
        assert (df_centroids == df_centroids.iloc[0]).all().all()
    
    # Calibrate the motors
    motor.calibrate(start, stop, steps, RE=fresh_RE, detector=camera,
                    average=1, tolerance=0, confirm_overwrite=False)
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))    
