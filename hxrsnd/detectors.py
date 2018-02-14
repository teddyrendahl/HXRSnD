"""
Detector classes
"""
import logging

from ophyd.areadetector.base import ADComponent

from pcdsdevices.epics.pim import PIMPulnixDetector
from pcdsdevices.epics.areadetector.cam import CamBase
from pcdsdevices.epics.areadetector.detectors import DetectorBase

from .snddevice import SndDevice

logger = logging.getLogger(__name__)

# Cam Classes

class GigeCam(CamBase, SndDevice):
    pass

# Detector Classes

class GigeDetector(DetectorBase, SndDevice):
    """
    Gige detector class.
    """
    cam = ADComponent(GigeCam, ":")


class OpalDetector(PIMPulnixDetector, SndDevice):
    """
    Opal detector class.
    """
    def __init__(self, prefix, read_attrs=["stats2"], *args, **kwargs):
        super().__init__(prefix, read_attrs=read_attrs, *args, **kwargs)
