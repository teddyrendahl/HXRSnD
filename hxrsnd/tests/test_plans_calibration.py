import logging

import numpy as np
import pytest
import pandas as pd
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

from .conftest import SynCamera
from ..plans import calibration as calib

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_calibration_centroid_scan(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        df = yield from calib.calibration_centroid_scan(
            camera, delay, [m1, m2], -1, 1, 3, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])
        assert True not in df.isnull().values
        print(df)
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
    def test_plan():
        calib_motors = [m1,m2]
        df_scan = yield from calib.calibration_centroid_scan(
            camera, delay, calib_motors, -1, 1, 3, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])
        
        # Get the current positions of the calib motors
        expected_positions = [m.position for m in calib_motors]
        # Perform the walk
        _, start = yield from calib.detector_scaling_walk(
            df_scan, camera, delay, calib_motors, tolerance=0)

        # Make sure we dont have any bad values
        assert np.nan not in start and np.inf not in start
        # Make sure we are get the expected positions of the motors
        assert start == expected_positions
        
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

@pytest.mark.parametrize("weights", [(1,1), (.5,-.5), (-10,5.5)])
def test_detector_scaling_walk_scale_values_are_valid(fresh_RE, weights):
    camera = SynCamera(m1, m2, delay, name="camera")
    centroids = [camera.centroid_x, camera.centroid_y]
    
    for cent, weight in zip(centroids, weights):
        cent.weights = [weight, cent.weights[1]]
    
    def test_plan():
        calib_motors = [m1,m2]
        df_scan = yield from calib.calibration_centroid_scan(
            camera, delay, calib_motors, -1, 1, 3, detector_fields=[
                'camera_centroid_x',
                'camera_centroid_y'])

        # Get the expected scales if we do the walk
        expected_scales = [1/cent.weights[0] for cent in centroids]
        # Perform the walk
        scales, _ = yield from calib.detector_scaling_walk(
            df_scan, camera, delay, [m1,m2], tolerance=0)

        # Make sure we dont have any bad values
        assert np.nan not in scales and np.inf not in scales
        # Make sure we are get the expected positions of the motors
        assert np.isclose(scales, expected_scales, rtol=0.0001).all()
                
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))
    
    
        
