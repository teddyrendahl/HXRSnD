"""
Tests for the scripts file in the top level directory
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import pytest
from ophyd.tests.conftest import using_fake_epics_pv
import numpy as np

##########
# Module #
##########
from .conftest import requires_epics
from hxrsnd.utils import absolute_submodule_path


def scripts_import():
    # Get the absolute path to the scripts file
    scripts_local_path = "HXRSnD/scripts.py"
    scripts_abs_path = absolute_submodule_path(scripts_local_path)
    # Try importing the snd_file
    import importlib.util
    spec = importlib.util.spec_from_file_location("scripts", scripts_abs_path)
    snd_scripts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snd_scripts)


@pytest.mark.timeout(60)
@requires_epics
def test_scripts_import_with_epics():
    scripts_import()


@pytest.mark.timeout(60)
@using_fake_epics_pv
def test_scripts_import_no_epics():
    scripts_import()
