# from bluesky import RunEngine

# from pcdsdevices.daq import make_daq_run_engine

from hxrsnd.sndmotor import SamMotor
from hxrsnd.sequencer import SeqBase
from hxrsnd.sndsystem import SplitAndDelay
from hxrsnd.detectors import OpalDetector

# Base PV
pv_base = "XCS:SND"

# Instantiate the whole system
snd = SplitAndDelay(pv_base)
daq = snd.daq

# Create a RunEngine
# RE = RunEngine({})
# RE_daq = make_daq_run_engine(snd.daq)

# Additional Devices
seq = SeqBase("ECS:SYS0:4", desc="Sequencer Channel 4")
sam_x = SamMotor("XCS:USR:MMN:01", name="sam_x")
sam_y = SamMotor("XCS:USR:MMN:02", name="sam_y")
opal_1 = OpalDetector("XCS:USR:O1000:01", name="Opal 1")
