############
# Standard #
############
import asyncio
import sys
import time
import copy
import random
import logging
import inspect
import threading
from functools import wraps

###############
# Third Party #
###############
import pytest
from bluesky.run_engine import RunEngine
from bluesky.tests.conftest import RE
import epics
import numpy as np
import epics

########
# SLAC #
########
from pcdsdevices.sim.pv import  using_fake_epics_pv

##########
# Module #
##########

# Define the requires epics
try:
    import epics
    pv = epics.PV("XCS:USR:MMS:01")
    try:
        val = pv.get()
    except:
        val = None
except:
    val = None
epics_subnet = val is not None
requires_epics = pytest.mark.skipif(not epics_subnet,
                                    reason="Could not connect to sample PV")

#Enable the logging level to be set from the command line
def pytest_addoption(parser):
    parser.addoption("--log", action="store", default="INFO",
                     help="Set the level of the log")
    parser.addoption("--logfile", action="store", default=None,
                     help="Write the log output to specified file path")

#Create a fixture to automatically instantiate logging setup
@pytest.fixture(scope='session', autouse=True)
def set_level(pytestconfig):
    #Read user input logging level
    log_level = getattr(logging, pytestconfig.getoption('--log'), None)

    #Report invalid logging level
    if not isinstance(log_level, int):
        raise ValueError("Invalid log level : {}".format(log_level))

    #Create basic configuration
    logging.basicConfig(level=log_level,
                        filename=pytestconfig.getoption('--logfile'))

@pytest.fixture(scope='function')
def fresh_RE(request):
    return RE(request)


def get_classes_in_module(module, subcls=None, blacklist=None):
    classes = []
    blacklist = blacklist or list()
    all_classes = [(_, cls) for (_, cls) in inspect.getmembers(module)
                          if cls not in blacklist]
    for _, cls in all_classes:
        try:
            if cls.__module__ == module.__name__:
                if subcls is not None:
                    try:
                        if not issubclass(cls, subcls):
                            continue
                    except TypeError:
                        continue
                classes.append(cls)
        except AttributeError:
            pass
    return classes

# Create a fake epics device
@using_fake_epics_pv
def fake_device(device, name="TEST"):
    return device(name, name=name)

