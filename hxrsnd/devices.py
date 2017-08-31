"""
Script to hold the split and delay devices.
"""
############
# Standard #
############
import logging
from enum import Enum

###############
# Third Party #
###############
import numpy as np
from ophyd.utils.epics_pvs import raise_if_disconnected
from ophyd.status import wait as status_wait

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.component import Component
from pcdsdevices.epics.rtd import OmegaRTD
from pcdsdevices.epics.aerotech import (RotationAero, LinearAero)
from pcdsdevices.epics.attocube import (TranslationEcc, GoniometerEcc, DiodeEcc)
from pcdsdevices.epics.diode import (HamamatsuDiode, HamamatsuXMotionDiode,
                                     HamamatsuXYMotionCamDiode)

##########
# Module #
##########
from .bragg import bragg_angle
from .state import OphydMachine

logger = logging.getLogger(__name__)


class TowerBase(Device):
    """
    Base tower class.
    """
    def E_to_theta(self, E, ID="Si", hkl=(2,2,0)):
        """
        Computes theta1 based on the inputted energy. This should function
        as a lookup table.
        
        Parmeters
        ---------
        E : float
        	Energy to convert to theta1

        ID : str, optional
            Chemical fomula : 'Si'

        hkl : tuple, optional
            The reflection : (2,2,0)

        Returns
        -------
        theta1 : float
            Expected bragg angle for E
        """
        self.E = E
        return bragg_angle(E=E, ID=ID, hkl=hkl)

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)
        self.theta = self.position

    @property
    def energy(self):
        """
        Sets angle of the tower according to the inputted energy.

        Returns
        -------
        E : float
        	Energy of the delay line.
        """
        return bragg_energy(self.position)

    @energy.setter
    def energy(self, E):
        """
        Placeholder for the energy setter. Implement for each TowerBase
        subclass.
        """
        pass
    
    @property
    def position(self):
        """
        Current position of the tower. Implment this for each TowerBase
        subclass.
        """
        return None


class DelayTower(TowerBase):
    """
    Delay Tower

    # TODO: Fully fill in components
    
    Components
    ----------
    tth : RotationAero
    	Rotation axis of the entire delay arm

    th1 : RotationAero
    	Rotation axis of the static crystal

    th2 : RotationAero
    	Rotation axis of the delay crystal

    x : LinearAero
    	Linear stage for insertion/bypass of the tower

    L : LinearAero
    	Linear stage for the delay crystal

    y1 : TranslationEcc
    	Y translation for the static crystal

    y2 : TranslationEcc
    	Y translation for the delay crystal

    chi1 : GoniometerEcc
    	Goniometer on static crystal

    chi2 : GoniometerEcc
    	Goniometer on delay crystal

    dh : DiodeEcc
    	Diode insertion motor

    diode : HamamatsuDiode
    	Diode between the static and delay crystals

    temp : OmegaRTD
    	RTD temperature sensor for the nitrogen.    
    """
    # Rotation stages
    tth = Component(RotationAero, ":TTH")
    th1 = Component(RotationAero, ":TH1")
    th2 = Component(RotationAero, ":TH2")

    # Linear stages
    x = Component(LinearAero, ":X")
    L = Component(LinearAero, ":L")

    # Y Crystal motion
    y1 = Component(TranslationEcc, ":Y1")
    y2 = Component(TranslationEcc, ":Y2")

    # Chi motion
    chi1 = Component(GoniometerEcc, ":CHI1")
    chi2 = Component(GoniometerEcc, ":CHI2")

    # Diode motion
    dh = Component(DiodeEcc, ":DH")

    # Diode
    diode = Component(HamamatsuDiode, ":DIODE")

    # Temperature monitor
    temp = Component(OmegaRTD, ":TEMP")

    @property
    def position(self):
        """
        Returns the theta position of the arm (tth) in degrees.

        Returns
        -------
        position : float
        	Position of the arm in degrees.
        """
        return self.tth.position

    @TowerBase.energy.setter
    def energy(self, E):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        # Convert to theta1
        # TODO: Error handling here
        self.theta = self.E_to_theta(E)

        logger.debug("\nMoving {tth} to {theta1} \nMoving {th1} and {th2} to "
                     "{half_theta1}.".format(
                         tth=self.tth.name, th1=self.th1.name, th2=self.th2.name,
                         theta1=self.theta1, half_theta1=self.theta1/2))

        # Set the position of the motors
        status_tth = self.tth.move(self.theta, wait=False)
        status_th1 = self.th1.move(self.theta/2, wait=False)
        status_th2 = self.th2.move(self.theta/2, wait=False)
    

class ChannelCutTower(TowerBase):
    """
    Channel Cut tower.

    Components
    ----------
    th : RotationAero
    	Rotation stage of the channel cut crystal

    x : LinearAero
    	Translation stage of the tower
    """
    # Rotation
    th = Component(RotationAero, ":TH")

    # Translation
    x = Component(LinearAero, ":X")

    @property
    def position(self):
        """
        Returns the theta position of the crystal (th) in degrees.

        Returns
        -------
        position : float
        	Position of the arm in degrees.
        """
        return self.th.position

    @TowerBase.energy.setter
    def energy(self, E):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        # Convert to theta
        # TODO: Error handling here
        self.theta = self.E_to_theta(E)

        logger.debug("\nMoving {th} to {theta}".format(
            th=self.th.name, theta=self.theta))

        # Set the position of the motors on tower 2
        status_t2_th = t2.th.move(self.theta/2, wait=False)

        
class SplitAndDelay(Device):
    """
    Hard X-Ray Split and Delay System.

    Components
    ----------
    t1 : DelayTower
    	Tower 1 in the split and delay system

    t4 : DelayTower
    	Tower 4 in the split and delay system

    t2 : ChannelCutTower
    	Tower 2 in the split and delay system

    t3 : ChannelCutTower
    	Tower 3 in the split and delay system

    di : HamamatsuXYMotionCamDiode
    	Input diode for the system
    
    dd : HamamatsuXYMotionCamDiode
    	Diode between the two delay towers

    do : HamamatsuXYMotionCamDiode
    	Output diode for the system

    dci : HamamatsuXMotionDiode
    	Input diode for the channel cut line
    
    dcc : HamamatsuXMotionDiode
    	Diode between the two channel cut towers
    
    dco : HamamatsuXMotionDiode
    	Input diode for the channel cut line
    """
    # Delay Towers
    t1 = Component(DelayTower, ":T1")
    t4 = Component(DelayTower, ":T4")

    # Channel Cut Towers
    t2 = Component(ChannelCutTower, ":T2")
    t3 = Component(ChannelCutTower, ":T3")

    # SnD and Delay line diodes
    di = Component(HamamatsuXYMotionCamDiode, ":DI")
    dd = Component(HamamatsuXYMotionCamDiode, ":DD")
    do = Component(HamamatsuXYMotionCamDiode, ":DO")

    # Channel Cut Diodes
    dci = Component(HamamatsuXMotionDiode, ":DCI")
    dcc = Component(HamamatsuXMotionDiode, ":DCC")
    dco = Component(HamamatsuXMotionDiode, ":DCO")
    
    # Constants
    c = 299792458               # m/s
    gap = 0.055                 # m
    min_dist = 0.105            # m

    def t_to_length(self, t, **kwargs):
        """
        Converts the inputted delay to the lengths on the delay arm linear
        stages.

        Parameters
        ----------
        t : float
        	The desired delay from the system in picoseconds

        Returns
        -------
        length : float
        	The distance between the delay crystal and the splitting or
        	recombining crystal.
        """
        # Lets internally keep track of this
        self.t = t * 1e-12      # Convert to seconds

        # TODO : Double check that this is correct
        length = ((self.t*self.c + 2*self.gap * (1 - np.cos(
            2*self.t1.th1.position))/np.sin(self.t1.th1.position))/
                  (2*(1 - np.cos(2*self.t3.th.position))))

        return length * 1000    # Convert to mm

    @property
    def energy(self):
        """
        Returns the energy the system is currently set to.

        Returns
        -------
        E1, E2 : tuple
        	Energy for the delay line and channel cut line.
        """
        return self.t1.energy, self.t2.energy

    @energy.setter
    def energy(self, E):
        """
        Sets the energy for both the delay line and the channe cut line of the
        system.

        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        self.t1.energy = E
        self.t2.energy = E
        self.t3.energy = E
        self.t4.energy = E

    @property
    def energy1(self):
        """
        Returns the calculated energy based on the angle of the delay line

        Returns
        -------
        E1 : float
        	Energy of the delay line.
        """
        return self.t1.energy

    @energy1.setter
    def energy1(self, E):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        self.t1.energy = E
        self.t4.energy = E
        
    @property
    def energy2(self):
        """
        Returns the calculated energy based on the angle of the channel cut
        line.

        Returns
        -------
        E : float
        	Energy of the channel cut line.
        """
        return self.t2.energy

    @energy2.setter
    def energy2(self, E):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        self.t2.energy = E
        self.t3.energy = E
        
    @property
    def delay(self):
        """
        Returns the current expected delay of the system.

        Returns
        -------
        t : float
        	Expected delay in picoseconds
        """
        # TODO: Replace with delay calculation.
        return self.t
        
    @delay.setter 
    def delay(self, t):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions.
        
        Parameters
        ----------
        t : float
        	The desired delay from the system.
        """
        self.length = self.t_to_length(t)

        logger.debug("Input delay: {0}. \nMoving t1.L and t2.L to {1}".format(
            t, self.length))

        status_t1_L = self.t1.L.move(self.length, wait=False)
        status_t4_L = self.t4.L.move(self.length, wait=False)

        # # Wait for the status objects to register the moves as complete
        # if wait:
        #     logger.info("Waiting for {} to finish move ...".format(self.name))
        #     # TODO: Wait on the composite status
        #     # status_wait(status_composite)
        
        # TODO: Find a way to create composite statuses
        # return status_composite

# Notes :
# - What is the gap?
# - How does the eq for t1.L and t4.L change for the correct system



        
