############
# Standard #
############
import logging

###############
# Third Party #
###############
import pytest
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

########
# SLAC #
########

##########
# Module #
##########
from .conftest import SynCamera
from ..plans.calibration import calibration_scan

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

@pytest.mark.parametrize("inputs", [(['centroid_x'], [m1]),
                                    (['centroid_x', 'centroid_y'], [m1,m2])])
def test_calibration_scan(fresh_RE, inputs):
    camera = SynCamera(m1, m2, delay, name="camera")
    def test_plan():
        df = yield from calibration_scan(camera, inputs[0], delay, inputs[1], 
                                         -5, 5, 11,)
    # Wrap the plan
    plan = run_wrapper(test_plan())
    # And now run it
    fresh_RE(plan)    

