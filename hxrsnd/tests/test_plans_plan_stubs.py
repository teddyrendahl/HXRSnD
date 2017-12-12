############
# Standard #
############
import math
import logging

###############
# Third Party #
###############
import numpy as np
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

########
# SLAC #
########

##########
# Module #
##########
from .conftest import SynCamera
from ..plans.plan_stubs import euclidean_distance

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
delay = SynAxis(name="delay")

def test_euclidean_distance(fresh_RE):
    camera = SynCamera(m1, m2, delay, name="camera")    
    # Define the distance plan that makes the assertion
    def test_plan():
        distance = yield from euclidean_distance(
            camera, ['centroid_x', 'centroid_y'], [1,1])
        assert np.isclose(distance, math.sqrt(2))
    
    # Wrap the plan
    plan = run_wrapper(test_plan())
    # And now run it
    fresh_RE(plan)

