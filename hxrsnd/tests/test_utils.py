"""
Tests for pyutils.pyutils
"""
import re
import logging
from pathlib import Path
from collections.abc import Iterable

import pytest
import numpy as np

from hxrsnd import utils

logger = logging.getLogger(__name__)

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
    abs_path = Path(utils.absolute_submodule_path(path, template))
    assert abs_path == Path("/".join(template.split("/")[:-3]) + "/" + path)
    
def test_stop_on_keyboardinterrupt_runs_stop_method():
    class TestClass:
        name = "test"
        stopped = False
        @utils.stop_on_keyboardinterrupt
        def something_that_raises_keyboardinterrupt(self):
            raise KeyboardInterrupt
        def stop(self):
            self.stopped = True
    tst = TestClass()
    assert tst.stopped == False
    tst.something_that_raises_keyboardinterrupt()
    assert tst.stopped == True

@pytest.mark.parametrize("value", [None, 10])
def test_none_if_no_parent_returns_the_correct_value(value):
    class Test:
        @utils.none_if_no_parent(value)
        def tst(self):
            return True
    tst = Test()
    tst.parent = None
    assert tst.tst() is value
    tst.parent = True
    assert tst.tst() is True
    
