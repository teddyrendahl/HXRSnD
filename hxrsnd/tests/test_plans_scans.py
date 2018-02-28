import logging

import pytest
from numpy import linspace
import pandas as pd
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

from .conftest import SynCamera
from ..plans.scans import centroid_scan
from ..utils import as_list

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_centroid_scan_returns_df(fresh_RE):
    # Simulated camera
    camera = SynCamera(m1, m2, delay, name="camera")
    # Create the plan
    def test_plan():
        delay_scan = (yield from centroid_scan(camera, delay, -1, 1, 3,
                                               detector_fields=[
                                                   'camera_centroid_x',
                                                   'camera_centroid_y']))        
        # Check that we got dataframe
        assert isinstance(delay_scan, pd.DataFrame)
        # Check that all the entries were written to and none are nans
        assert True not in delay_scan.isnull().values
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

@pytest.mark.parametrize("steps", [3, 11])
@pytest.mark.parametrize("stop", [5, 10])    
@pytest.mark.parametrize("start", [-5, -10])
def test_centroid_scan_returns_correct_df_index(fresh_RE, start, stop, steps):
    # Simulated camera
    camera = SynCamera(m1, m2, delay, name="camera")
    # Create the plan
    def test_plan():
        delay_scan = (yield from centroid_scan(camera, delay, start, stop,
                                               steps, detector_fields=[
                                                   'camera_centroid_x',
                                                   'camera_centroid_y']))
        # Check the number of steps
        assert delay_scan.shape[0] == steps
        # Check all the values are equal to linspace
        assert (delay_scan.index.values == linspace(start, stop, steps)).all()
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

@pytest.mark.parametrize("system_attrs", [([], []),
                                          (m1, m1.name),
                                          ([m1, m2], [m1.name, m2.name])])
@pytest.mark.parametrize("mot_fields", ['',
                                        'delay',
                                        ['delay', 'delay_setpoint']])
@pytest.mark.parametrize("det_fields", ['centroid_x',
                                        ['centroid_x',
                                         'centroid_y']])
def test_centroid_scan_returns_correct_columns(fresh_RE, mot_fields, det_fields,
                                               system_attrs):
    # Simulated camera
    camera = SynCamera(m1, m2, delay, name="camera")
    # Create the plan
    def test_plan():
        steps = 2               # Start and stop position
        delay_scan = (yield from centroid_scan(camera, delay, -1, 1, steps,
                                               detector_fields=det_fields,
                                               motor_fields=mot_fields,
                                               system=system_attrs[0],
                                               system_fields=system_attrs[1]))

        expected_length = (len(as_list(mot_fields)) or 1) \
                           + len(as_list(det_fields)) \
                           + len(as_list(system_attrs[1]))
        # Check the number of columns based in the inputs
        assert delay_scan.shape[1] == expected_length
        
        expected_columns = as_list(mot_fields or delay.name) \
                            + as_list(system_attrs[1]) \
                            + ["_".join([camera.name, fld]) for fld in as_list(
                                det_fields)]
        # Check the columns are all what we expect them to be 
        assert (delay_scan.columns == expected_columns).all()
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))
