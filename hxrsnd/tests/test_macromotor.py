#!/usr/bin/env python
# -*- coding: utf-8 -*-
############
# Standard #
############
import logging
import time
import pytest

###############
# Third Party #
###############
import numpy as np
from ophyd.device import Device

########
# SLAC #
########
from pcdsdevices.sim.pv import using_fake_epics_pv

##########
# Module #
##########
from .conftest import get_classes_in_module, fake_device
from hxrsnd.macromotor import MacroBase
from hxrsnd.sndsystem import SplitAndDelay

logger = logging.getLogger(__name__)

@using_fake_epics_pv
def test_macromotors_instantiate_and_run_ophyd_functions():
    snd = fake_device(SplitAndDelay)
    for comp_name in snd.component_names:
        component = getattr(snd, comp_name)
        if issubclass(type(component), MacroBase):
            assert(isinstance(component.read(), dict))
            assert(isinstance(component.describe(), dict))
            assert(isinstance(component.describe_configuration(), dict))
            assert(isinstance(component.read_configuration(), dict))
