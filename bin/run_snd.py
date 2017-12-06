"""
HXRSnD IPython Shell
"""
############
# Standard #
############
import os
import socket
import logging
from imp import reload
from pathlib import Path
import warnings
###############
# Third Party #
###############
from bluesky import RunEngine
from bluesky.preprocessors import run_wrapper

########
# SLAC #
########
from pcdsdevices.daq import make_daq_run_engine

##########
# Module #
##########
from hxrsnd.plans import linear_scan
from hxrsnd.sndmotor import SamMotor
from hxrsnd.sequencer import SeqBase
from hxrsnd.utils import setup_logging
from hxrsnd.sndsystem import SplitAndDelay

# Ignore python warnings
warnings.filterwarnings('ignore')

# Logging
setup_logging()
logger = logging.getLogger("hxrsnd")

try:
    # Base PV
    pv_base = "XCS:SND"
    # Instantiate the whole system
    snd = SplitAndDelay(pv_base)
    # Create a RunEngine
    RE = RunEngine({})
    RE_daq = make_daq_run_engine(snd.daq)
    # Additional Devices
    seq = SeqBase("ECS:SYS0:4", desc="Sequencer Channel 4")
    sam_x = SamMotor("XCS:USR:MMN:01", name="sam_x")
    sam_y = SamMotor("XCS:USR:MMN:02", name="sam_y")
    # Success
    logger.debug("Successfully created SplitAndDelay class on '{0}'".format(
        socket.gethostname()))

except Exception as e:
    logger.error("Failed to create SplitAndDelay class on '{0}'. Got error: "
                 "{1}".format(socket.gethostname(), e))
    raise

# Try importing from the scripts file if we succeeded at making the snd object
else:
    try:
        path_scripts = Path(os.path.dirname(__file__)) / "../scripts.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scripts", path_scripts)
        from scripts import *
        logger.debug("Successfully loaded scripts.")
    # There was some problem in the file
    except Exception as e:
        logger.warning("Failed to load scripts file, got the following error: "
                       "{0}".format(e))
        raise
    # Notify the user that everything went smoothly
    else:
        logger.info("Successfully initialized new SnD session on '{0}'".format(
            socket.gethostname()))
