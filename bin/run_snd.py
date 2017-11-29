############
# Standard #
############
import logging
from imp import reload
from logging.handlers import RotatingFileHandler
from pathlib import Path
import socket

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
from hxrsnd.utils import setup_logging
from hxrsnd.pneumatic import SndPneumatics
from hxrsnd.sndsystem import SplitAndDelay
from hxrsnd.tower import DelayTower, ChannelCutTower
from hxrsnd.bragg import bragg_angle, bragg_energy, sind, cosd
from hxrsnd.diode import HamamatsuXMotionDiode, HamamatsuXYMotionCamDiode

logger = logging.getLogger(__name__)

try:
    # Base PV
    pv_base = "XCS:SND"
    # Instantiate the whole system
    snd = SplitAndDelay(pv_base)
    # Create a RunEngine
    RE = RunEngine({})
    RE_daq = make_daq_run_engine(snd.daq)

    # Logging
    setup_logging()
    logger = logging.getLogger("hxrsnd")
    logger.info("Successfully initialized new SnD session on '{0}'".format(
        socket.gethostname()))
except Exception as e:
    logging.error(e)
    raise
