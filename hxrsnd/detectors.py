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
from .utils import get_logger

logger = get_logger(__name__)


class GigeCam(CamBase):
    def __init__(self, prefix, name=None, desc=None, *args, **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name        


class GigeDetector(DetectorBase):
    """
    Gige Cam detector class.
    """
    cam = ADComponent(GigeCam, ":")
    def __init__(self, prefix, name=None, desc=None, *args, **kwargs):
        self.desc = desc or name
        super().__init__(prefix, name=name, *args, **kwargs)
        if self.desc is None:
            self.desc = self.name        
