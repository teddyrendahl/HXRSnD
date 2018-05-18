import logging

import pytest
from bluesky.plan_stubs import rel_set
from bluesky.preprocessors  import run_wrapper
from ophyd.sim import SynAxis

from ..plans.preprocessors import return_to_start

logger = logging.getLogger(__name__)

m1 = SynAxis(name="m1")
m2 = SynAxis(name="m2")
motors = [m1, m2]

@pytest.mark.parametrize("return_devices", [[], [m1], [m1,m2]])
def test_return_to_start_returns_motors_correctly(fresh_RE, return_devices):
    # Grab the initial positions
    initial_positions = [mot.position for mot in motors]
    final_positions = []
    # Create the plan
    @return_to_start(*return_devices)
    def test_plan():
        for mot in motors:
            yield from rel_set(mot, 1)
            # Grab the final positions
            final_positions.append(mot.position)
                              
    # Run the plan
    fresh_RE(run_wrapper(test_plan()))

    # get the expected and current positions
    expected_positions = [ipos if m in return_devices else fpos 
                          for m, ipos, fpos in zip(
                              motors, initial_positions, final_positions)]
    current_positions = [mot.position for mot in motors]

    # Assert they are the same
    assert current_positions == expected_positions
