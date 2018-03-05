import logging

import numpy as np
import pytest
import pandas as pd
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

from .conftest import SynCamera, test_df_scan
from ..plans import calibration as calib

logger = logging.getLogger(__name__)

rtol = 1e-6                             # Numpy relative tolerance
m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_calibration_centroid_scan_df_is_valid(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        df = yield from calib.calibration_centroid_scan(
            camera, delay, [m1, m2], -1, 1, 5, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])
        assert True not in df.isnull().values
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

def test_calibration_centroid_scan_raises_ValueError_correctly(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        with pytest.raises(ValueError):
            df = yield from calib.calibration_centroid_scan(
                camera, delay, [m1, m2], -1, 1, 3, calib_fields=[m1.name], 
                detector_fields=['camera_centroid_x', 'camera_centroid_y'])
        with pytest.raises(ValueError):
            df = yield from calib.calibration_centroid_scan(
                camera, delay, [m1, m2], -1, 1, 3, calib_fields=[m1.name]*3,
                detector_fields=['camera_centroid_x', 'camera_centroid_y'])

def test_calibration_centroid_scan_renames_columns_correctly(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        calib_motors = [m1, m2]
        df = yield from calib.calibration_centroid_scan(
            camera, delay, calib_motors, -1, 1, 3, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])
        expected_columns = [delay.name] + [m+"_pre" for m in calib_motors] \
                           + detector_fields
        assert (df.columns == expected_columns).all()                               
    
def test_detector_scaling_walk_start_positions_are_valid(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    calib_motors = [m1,m2]
    def test_plan():        
        # Get the current positions of the calib motors
        expected_positions = [test_df_scan[m.name+"_pre"][-1]
                              for m in calib_motors]
        # Perform the walk
        _, start = yield from calib.detector_scaling_walk(
            test_df_scan, camera, calib_motors, tolerance=0, system=delay)

        # Make sure we dont have any bad values
        assert np.nan not in start and np.inf not in start
        # Make sure we are get the expected positions of the motors
        assert np.isclose(start, expected_positions, rtol=rtol).all()
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

@pytest.mark.parametrize("weights", [(1,1), (.5,-.5), (-10,5.5)])
def test_detector_scaling_walk_scale_values_are_valid(fresh_RE, weights):
    camera = SynCamera(m1, m2, delay, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    calib_motors = [m1,m2]    
    for cent, weight in zip(centroids, weights):
        cent.weights = [weight, cent.weights[1]]
    
    def test_plan():
        df_scan = yield from calib.calibration_centroid_scan(
            camera, delay, [m1, m2], -1, 1, 5, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])

        # Get the expected scales if we do the walk
        expected_scales = [1/cent.weights[0] for cent in centroids]
        # Perform the walk
        scales, _ = yield from calib.detector_scaling_walk(
            df_scan, camera, calib_motors, tolerance=0, system=delay)

        # Make sure we dont have any bad values
        assert np.nan not in scales and np.inf not in scales
        # Make sure we are get the expected positions of the motors
        assert np.isclose(scales, expected_scales, rtol=rtol).all()
                
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))
        
def test_build_calibration_df_creates_correct_df_columns(fresh_RE):
    test_scale = [1.0, 1.0]
    test_start = [0.25, -0.25]
    camera = SynCamera(m1, m2, delay, name="camera")
    # The resulting df should be the same columns with two new ones
    new_columns = [m.name+"_post" for m in [m1,m2]]

    scan_columns = list(test_df_scan.columns)
    expected_columns = [delay.name] + new_columns

    df_calib = calib.build_calibration_df(test_df_scan, test_scale, test_start, 
                                    camera)
    # Make sure we didn't mutate the original scan df
    assert (test_df_scan.columns == scan_columns).all()
    # Make sure we get what we expect
    assert (df_calib.columns == expected_columns).all()

@pytest.mark.parametrize("weights", [(1,1), (.5,-.5), (-10,5.5)])
def test_scale_scan_df_creates_correct_calibration_tables(fresh_RE, weights):
    camera = SynCamera(m1, m2, delay, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    calib_motors = [m1,m2]    
    for cent, weight in zip(centroids, weights):
        cent.weights = [weight, cent.weights[1]]
    
    def test_plan():
        # Perform the scan
        df_scan = yield from calib.calibration_centroid_scan(
            camera, delay, [m1, m2], -1, 1, 5, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])

        # Perform the walk
        scales, starts = yield from calib.detector_scaling_walk(
            df_scan, camera, calib_motors, tolerance=0, system=delay)
        
        # Get the scaled scan dataframe
        df_calib = calib.build_calibration_df(df_scan, scales, starts, camera)

        # Expected positions of the centroids are the first positions
        expected_centroids = df_scan[[c.name for c in centroids]].iloc[0]

        for i in range(len(df_scan)):
            # Save the initial positions
            starting_pos = {m.name : m.position for m in [m1,m2]}
            # Move to the scan position for the main motor
            delay.set(df_calib[delay.name].iloc[i])

            for cmotor, exp_cent, cent in zip(calib_motors, expected_centroids, 
                                              centroids):
                # Move to the abosolute corrected position
                cmotor.set(df_calib[cmotor.name+"_post"].iloc[i])
                # Check the centroids are where they should be
                assert np.isclose(cent.get(), exp_cent, rtol=rtol)

    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

@pytest.mark.parametrize("weights", [(1,1), (.5,-.5), (-10,5.5)])
def test_calibration_scan(fresh_RE, weights):
    camera = SynCamera(m1, m2, delay, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    calib_motors = [m1,m2]    
    for cent, weight in zip(centroids, weights):
        cent.weights = [weight, cent.weights[1]]

    def test_plan():
        # Perform the scan
        df_calib, df_scan, _, _ = yield from calib.calibration_scan(
            camera, ['camera_centroid_x','camera_centroid_y'], delay, None,
            [m1,m2], None, -1, 1, 5, tolerance=0)

        # Expected positions of the centroids are the first positions
        expected_centroids = df_scan[[c.name for c in centroids]].iloc[0]

        for i in range(len(df_scan)):
            # Save the initial positions
            starting_pos = {m.name : m.position for m in calib_motors}
            # Move to the scan position for the main motor
            delay.set(df_calib[delay.name].iloc[i])

            for cmotor, exp_cent, cent in zip(calib_motors, expected_centroids, 
                                              centroids):
                # Move to the abosolute corrected position
                cmotor.set(df_calib[cmotor.name+"_post"].iloc[i])
                # Check the centroids are where they should be
                assert np.isclose(cent.get(), exp_cent, rtol=rtol)

    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

def test_calibrate_motor(fresh_RE, get_calib_motor):
    # Should be properly configured to start
    motor = get_calib_motor
    camera = SynCamera(*motor.calib_motors, motor, name="camera")
    calib_motors = motor.calib_motors
    start, stop, steps = -1, 1, 5

    def test_plan():
        # Perform the scan to get the expected scan results
        df_calib, df_scan, scale, start_pos = yield from calib.calibration_scan(
            camera,
            motor.detector_fields,
            motor,
            motor.motor_fields,
            motor.calib_motors,
            motor.calib_fields,
            start, stop, steps,
            tolerance=0)
        
        # Calibrate the motor
        _, _ = yield from calib.calibrate_motor(
            camera,
            motor.detector_fields,
            motor,
            motor.motor_fields,
            motor.calib_motors,
            motor.calib_fields,
            start, stop, steps,
            confirm_overwrite=False,
            tolerance=0)

        # Get the configuration from the motor as it sees it
        config = motor.read_configuration()

        # Ensure the resulting config is what we got in the initial scan
        assert config['calib']['value'].equals(df_calib)
        assert config['scan']['value'].equals(df_scan)
        assert config['motors']['value'] == [motor] + calib_motors
        assert config['scale']['value'] == scale
        assert config['start']['value'] == start_pos
        
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))
