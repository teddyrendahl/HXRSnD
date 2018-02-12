"""
HXRSnD IPython Shell
"""
import os
import socket
import logging
from imp import reload
from pathlib import Path
import warnings
from hxrsnd.utils import setup_logging

# Ignore python warnings (Remove when ophyd stops warning about 'signal_names')
warnings.filterwarnings('ignore')

# Logging
setup_logging()
logger = logging.getLogger("hxrsnd")

try:
    from snd_devices import *
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
