"""
Tests for pyutils.pyutils
"""
############
# Standard #
############
import re
import logging
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

test_values = [2, np.pi, True, "test_s", "10", ["test"], ("test",), {"test":1}]
test_lists = [[1,2,3,4,5], [[1],[2],[3],[4],[5]], [[1,2,3],[4,5]],
              [[1,[2,[3,[4,[5]]]]]]])

@pytest.mark.parametrize("test", test_values)
def test_isiterable_correctly_returns(test):
    iterable = pyutils.isiterable(test)
    if isinstance(test, str):
        assert iterable is False
    elif isinstance(test, Iterable):
        assert iterable is True
    else:
        assert iterable is False

@pytest.mark.parametrize("test", test_list)
def test_flatten_works_correctly(test):
    assert pyutils.flatten(test) == [1,2,3,4,5]
        
