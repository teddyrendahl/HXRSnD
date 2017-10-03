"""
Tests for pyutils.pyutils
"""
############
# Standard #
############
import re
import logging
import pathlib
from collections.abc import Iterable

###############
# Third Party #
###############
import pytest
import numpy as np

##########
# Module #
##########
from hxrsnd import utils
from hxrsnd.utils import get_logger

logger = get_logger(__name__, log_file=False)

test_values = [2, np.pi, True, "test_s", "10", ["test"], ("test",), {"test":1}]
test_lists = [[1,2,3,4,5], [[1],[2],[3],[4],[5]], [[1,2,3],[4,5]],
              [[1,[2,[3,[4,[5]]]]]]]

@pytest.mark.parametrize("test", test_values)
def test_isiterable_correctly_returns(test):
    iterable = utils.isiterable(test)
    if isinstance(test, str):
        assert iterable is False
    elif isinstance(test, Iterable):
        assert iterable is True
    else:
        assert iterable is False

@pytest.mark.parametrize("test", test_lists)
def test_flatten_works_correctly(test):
    assert utils.flatten(test) == [1,2,3,4,5]

@pytest.mark.parametrize("screen", ["motor_expert_screen.sh", "snd_main"])
def test_absolute_submodule_path_works_correctly(screen):
    path = "HXRSnD/screens/{0}".format(screen)
    template = "/reg/neh/operator/xcsopr/bin/snd/HXRSnD/hxrsnd/utils.py"
    abs_path = utils.absolute_submodule_path(path, template)
    assert abs_path == ("/".join(template.split("/")[:-3]) + "/" + path)
    
