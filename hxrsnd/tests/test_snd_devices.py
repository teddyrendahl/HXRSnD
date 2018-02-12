"""
Tests for the bin ipython shell
"""
import logging
import sys

import pytest
from ophyd.signal import Signal
from ophyd.device import Component as Cmp
from ophyd.tests.conftest import using_fake_epics_pv
import numpy as np

from .conftest import requires_epics
from hxrsnd.detectors import OpalDetector
from hxrsnd.utils import absolute_submodule_path

logger = logging.getLogger(__name__)

def snd_devices_import():
    for comp in (OpalDetector.image1, OpalDetector.image2, OpalDetector.stats2):
        plugin_class = comp.cls
        plugin_class.plugin_type = Cmp(Signal, value=plugin_class._plugin_type)
    import snd_devices
    
@pytest.mark.timeout(60)
@requires_epics
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6")
def test_snd_devices_import_with_epics():
    snd_devices_import()

@pytest.mark.timeout(60)
@using_fake_epics_pv
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6")
def test_snd_devices_import_no_epics():
    snd_devices_import()
