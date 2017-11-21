############
# Standard #
############
import logging
from imp import reload
from logging.handlers import RotatingFileHandler
from pathlib import Path

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

#Logging
setup_logging()
logger = logging.getLogger("hxrsnd")

try:
    # Instantiate the system
    pv_base = "XCS:SND"

    # The whole system
    snd = SplitAndDelay(pv_base)

    # # Towers
    # t1 = DelayTower(pv_base + ":T1", y1="A:ACT0", y2="A:ACT1", chi1="A:ACT2",
    #                 chi2="B:ACT0", dh="B:ACT1", pos_inserted=21.1,
    #                 pos_removed=0, desc="Tower 1")
    # t2 = ChannelCutTower(pv_base + ":T2", pos_inserted=None, pos_removed=0, 
    #                      desc="Tower 2")
    # t3 = ChannelCutTower(pv_base + ":T3", pos_inserted=None, pos_removed=0, 
    #                      desc="Tower 3")
    # t4 = DelayTower(pv_base + ":T4", y1="C:ACT0", y2="C:ACT1", chi1="C:ACT2",
    #                 chi2="D:ACT0", dh="D:ACT1", pos_inserted=21.1,
    #                 pos_removed=0, desc="Tower 4")

    # # Vacuum
    # ab = SndPneumatics(pv_base)

    # # Diagnostics
    # di = HamamatsuXMotionDiode(pv_base + ":DIA:DI")
    # dd = HamamatsuXYMotionCamDiode(pv_base + ":DIA:DD")
    # do = HamamatsuXMotionDiode(pv_base + ":DIA:DO")
    # dci = HamamatsuXMotionDiode(pv_base + ":DIA:DCI")
    # dcc = HamamatsuXYMotionCamDiode(pv_base + ":DIA:DCC")
    # dco = HamamatsuXMotionDiode(pv_base + ":DIA:DCO")

    # Create a RunEngine
    RE = RunEngine({})
    RE_daq = make_daq_run_engine(snd.daq)

    logger.info("Successfully initialized new SnD session.")

except Exception as e:
    logger.error(e)
    raise

# These are the calculations provided by Yanwen. They can be a useful sanity
# check if things are being weird.

def snd_L(E1, E2, delay, gap=55):
    """
    Calculates the theta angles of the towers and the delay length based on the
    desired energy and delay.
    """
    cl = 0.3
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
        # gap is the distance between the two faces of the channel cut crystal
    L = (delay*cl/2.+gap*(1-cosd(2*theta_cc))/sind(theta_cc))/(1-cosd(2*theta_L))
    print ("t1.L = t4.L = {} mm".format(L))
    print ("t1.tth = t4.tth = {} degree".format(2*theta_L))
    print ("t1.th1=t1.th2=t4.th1=t4.th2 = {} degree".format(theta_L))
    print ("t2.th=t3.th = {} degree".format(theta_cc))
    return theta_L, theta_cc, L

def snd_diag(E1, E2, delay, gap=55):
    """
    Calculates the positions of the middle diagnostics of the system based on
    the inputted energy and delay.
    """
    cl = 0.3
    # speed of light
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
    dcc_x = 2*cosd(theta_cc)*gap
    L = (delay*cl/2.+gap*(1-cosd(2*theta_cc))/sind(theta_cc))/(1-cosd(2*theta_L))
    dd_x = -L*sind(2*theta_L)
    print ("dd.x = {}".format(dd_x))
    print ("dcc.x = {}".format(dcc_x))
    return dd_x, dcc_x

def snd_delay(E1, E2, L, gap=55):
    """
    Calculates the delay of the system based on the inputted energies and the
    delay length.
    """
    cl = 0.3
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
    delay = 2*(L*(1-cosd(2*theta_L)) - gap*(1-cosd(2*theta_cc))/sind(theta_cc))/cl 
    return delay
