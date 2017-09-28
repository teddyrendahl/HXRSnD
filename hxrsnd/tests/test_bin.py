"""
Tests for pyutils.pyutils
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import pytest
import numpy as np

##########
# Module #
##########
from .conftest import requires_epics
from hxrsnd.utils import absolute_submodule_path

@requires_epics
def test_bin_import():
    # Get the absolute path to the bin file
    bin_local_path = "HXRSnD/bin/run_snd.py"
    bin_abs_path = absolute_submodule_path(bin_local_path)
    # Try importing the snd_file
    import importlib.util
    spec = importlib.util.spec_from_file_location("bin.run_snd", bin_abs_path)
    snd_bin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snd_bin)



