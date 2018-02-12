"""
Tests for the scripts file in the top level directory
"""
import logging

import pytest
from ophyd.tests.conftest import using_fake_epics_pv
import numpy as np

from .conftest import requires_epics
from hxrsnd.utils import absolute_submodule_path

logger = logging.getLogger(__name__)

def scripts_import():
    import scripts

@pytest.mark.timeout(60)
@requires_epics
def test_scripts_import_with_epics():
    scripts_import()

@pytest.mark.timeout(60)
@using_fake_epics_pv
def test_scripts_import_no_epics():
    scripts_import()
