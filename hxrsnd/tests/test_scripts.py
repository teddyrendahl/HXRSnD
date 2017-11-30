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
import numpy as np

##########
# Module #
##########
from hxrsnd.utils import absolute_submodule_path

def test_scripts_import():
    # Get the absolute path to the scripts file
    scripts_local_path = "HXRSnD/scripts.py"
    scripts_abs_path = absolute_submodule_path(scripts_local_path)
    # Try importing the snd_file
    import importlib.util
    spec = importlib.util.spec_from_file_location("scripts", scripts_abs_path)
    snd_scripts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snd_scripts)

