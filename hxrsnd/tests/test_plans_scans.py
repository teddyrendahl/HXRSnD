############
# Standard #
############
import logging

###############
# Third Party #
###############
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

########
# SLAC #
########

##########
# Module #
##########
from .conftest import SynCamera
from ..plans.scans import centroid_scan

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_centroid_scan(fresh_RE):
    # Simulated camera
    camera = SynCamera(m1, m2, delay, name="camera")
    # Create the plan
    def test_plan():
        delay_scan = (yield from centroid_scan(camera, delay, -5, 5, 11))
        assert True not in delay_scan.isnull().values
    plan = run_wrapper(test_plan())
    # Run the plan
    fresh_RE(plan)

