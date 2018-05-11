"""
Tests for the bin ipython shell
"""
import logging
import sys

import pytest
from ophyd.tests.conftest import using_fake_epics_pv

from .conftest import requires_epics

logger = logging.getLogger(__name__)


@pytest.mark.timeout(60)
@requires_epics
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6")
def test_snd_devices_import_with_epics():
    import snd_devices


@pytest.mark.timeout(60)
@using_fake_epics_pv
@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6")
def test_snd_devices_import_no_epics():
    import snd_devices
