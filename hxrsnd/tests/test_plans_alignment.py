import logging

import numpy as np
from bluesky.preprocessors  import run_wrapper
from ophyd.sim              import SynAxis

from .conftest import Diode
from ..plans.alignment import maximize_lorentz, rocking_curve

logger = logging.getLogger(__name__)

crystal = SynAxis(name='angle')

def test_lorentz_maximize(fresh_RE):
    # Simulated diode readout
    diode = Diode('intensity', crystal, 'angle', 10.0, noise_multiplier=None)
    # Create plan to maximize the signal
    plan  = run_wrapper(maximize_lorentz(diode, crystal, 'intensity',
                                         step_size=0.2, bounds=(9., 11.),
                                         position_field='angle',
                                         initial_guess = {'center' : 8.}))
    # Run the plan
    fresh_RE(plan)

    # Trigger an update
    diode.trigger()
    #Check that we were within 10%
    assert np.isclose(diode.read()['intensity']['value'], 1.0, 0.1)

def test_rocking_curve(fresh_RE):
    # Simulated diode readout
    diode = Diode('intensity', crystal, 'angle', 10.0, noise_multiplier=None)
    # Create plan to maximize the signalplan
    plan  = run_wrapper(rocking_curve(diode, crystal, 'intensity',
                                      coarse_step=0.1, fine_step=0.05,
                                      bounds=(5., 15.), fine_space=2.5,
                                      position_field='angle',
                                      initial_guess = {'center' : 8.}))
    # Run the plan
    fresh_RE(plan)

    # Trigger an update
    diode.trigger()
    # Check that we were within 10%
    assert np.isclose(diode.read()['intensity']['value'], 1.0, 0.1)
