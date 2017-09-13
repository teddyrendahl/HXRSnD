############
# Standard #
############
import logging

###############
# Third Party #
###############
from ophyd.areadetector.base import ADComponent

########
# SLAC #
########
from pcdsdevices.epics.areadetector.cam import CamBase
from pcdsdevices.epics.areadetector.detectors import DetectorBase

##########
# Module #
##########

logger = logging.getLogger(__name__)


class GigeCam(CamBase):
    pass


class GigeDetector(DetectorBase):
    """
    Gige Cam detector class.
    """
    cam = ADComponent(GigeCam, ":")
