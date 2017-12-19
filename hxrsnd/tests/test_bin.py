"""
Tests for the bin ipython shell
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


def bin_import():
    # Get the absolute path to the bin file
    bin_local_path = "HXRSnD/bin/run_snd.py"
    bin_abs_path = absolute_submodule_path(bin_local_path)
    # Try importing the snd_file
    import importlib.util
    spec = importlib.util.spec_from_file_location("bin.run_snd", bin_abs_path)
    snd_bin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snd_bin)


@pytest.mark.timeout(60)
@requires_epics
def test_bin_import_with_epics():
    bin_import()


@pytest.mark.timeout(60)
@using_fake_epics_pv
def test_bin_import_no_epics():
    bin_import()
