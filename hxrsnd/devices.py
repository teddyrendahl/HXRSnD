"""
Script to hold the split and delay devices.
"""
############
# Standard #
############
import logging

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
from pcdsdevices.epics.diode import HamamatsuDiode
from pcdsdevices.epics.aerotech import (RotationAero, LinearAero)
from pcdsdevices.epics.attocube import (TranslationEcc, GoniometerEcc, DiodeEcc)

##########
# Module #
##########

logger = logging.getLogger(__name__)


class TowerBase(Device):
    """
    Base tower class.
    """
    pass


class DelayTower(TowerBase):
    """
    Delay Tower

    # TODO: Fully fill in components
    
    Components
    ----------
    r0 : RotationAero
    	Rotation axis of the entire delay arm

    r1 : RotationAero
    	Rotation axis of the static crystal

    r2 : RotationAero
    	Rotation axis of the delay crystal

    l0 : LinearAero
    	Linear stage for insertion/bypass of the tower

    l1 : LinearAero
    	Linear stage for the delay crystal

    y1 : TranslationEcc
    	Y translation for the static crystal

    y2 : TranslationEcc
    	Y translation for the delay crystal

    chi1 : GoniometerEcc
    	Goniometer on static crystal

    chi2 : GoniometerEcc
    	Goniometer on delay crystal

    d1 : DiodeEcc
    	Diode insertion motor

    diode : HamamatsuDiode
    	Diode between the static and delay crystals

    temp : OmegaRTD
    	RTD temperature sensor for the nitrogen.    
    """
    # Rotation stages
    r0 = Component(RotationAero, ":R0")
    r1 = Component(RotationAero, ":R1")
    r2 = Component(RotationAero, ":R1")

    # Linear stages
    l0 = Component(LinearAero, ":L0")
    l1 = Component(LinearAero, ":L1")

    # Y Crystal motion
    y1 = Component(TranslationEcc, ":Y1")
    y2 = Component(TranslationEcc, ":Y2")

    # Chi motion
    chi1 = Component(GoniometerEcc, ":CHI1")
    chi2 = Component(GoniometerEcc, ":CHI2")

    # Diode motion
    d1 = Component(DiodeEcc, ":D1")

    # Diode
    diode = Component(HamamatsuDiode, ":DIODE")

    # Temperature monitor
    temp = Component(OmegaRTD, ":TEMP")
    

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


class SnD(Device):
    """
    Hard X-Ray Split and Delay System.
    """
    t1 = component(DelayTower, ":T1")
    t2 = component(ChannelCutTower, ":T2")
    t3 = component(ChannelCutTower, ":T3")
    t4 = component(DelayTower, ":T4")

    # Constants
    c = 299792458               # m/s
    gap = 0.055                 # m
    min_dist = 0.105            # m

    def __init__(self, prefix, *, **kwargs):
        super().__init__(prefix, **kwargs)


    def e1_to_theta1(self, E1, **kwargs):
        """
        Computes theta1 based on the inputted energy. This should function
        as a lookup table.
        
        Parmeters
        ---------
        E1 : float
        	Energy to convert to theta1
        """
        # TODO: Find out what the conversion factor is
        # TODO: Add a check for energy
        return E1

    def e2_to_theta2(self, E2, **kwargs):
        """
        Computes theta2 based on the inputted energy. This should function
        as a lookup table.
        
        Parmeters
        ---------
        E2 : float
        	Energy to convert to theta2
        """
        # TODO: Find out what the conversion factor is
        # TODO: Add a check for energy
        return E2

    def t_to_length(self, t, **kwargs):
        """
        Converts the inputted delay to the lengths on the delay arm linear
        stages.

        Parameters
        ----------
        t : float
        	The desired delay from the system.

        Returns
        -------
        length : float
        	The distance between the delay crystal and the splitting or
        	recombining crystal.
        """
        # Lets internally keep track of this
        self.t = t
        
        length = ((t*self.c + 2*self.gap * (1 - np.cos(2*self.t1.r1.position))/
                   np.sin(self.t1.r1.position))/
                  (2*(1 - np.cos(2*self.t3.th.position))))

        # TODO: Length calculation checks
        return length

    def energy(self, E, **kwargs):
        """
        Sets the energy for both the delay line and the channe cut line of the
        system.

        Parmeters
        ---------
        E : float
        	Energy to use for the system.
        """
        status_e1 = self.energy1(E, **kwargs)
        status_e2 = self.energy2(E, **kwargs)
        return status_e1, status_e2
    

    def energy1(self, E1, wait=False, **kwargs):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E1 : float
        	Energy to use for the system.
        """
        # Convert to theta1
        # TODO: Error handling here
        self.theta1 = self.e1_to_theta1(E1)

        # Set the position of the motors on tower 1
        status_t1_r0 = t1.r0.move(2*self.theta1, wait=False)
        status_t1_r1 = t1.r1.move(self.theta1, wait=False)
        status_t1_r2 = t1.r2.move(self.theta1, wait=False)

        # Set the positions of the motors on tower 4
        status_t4_r0 = t4.r0.move(2*self.theta1, wait=False)
        status_t4_r1 = t4.r1.move(self.theta1, wait=False)
        status_t4_r2 = t4.r2.move(self.theta1, wait=False)

        # Wait for the status objects to register the moves as complete
        if wait:
            logger.info("Waiting for {} to finish move ...".format(self.name))
            # TODO: Wait on the composite status
            # status_wait(status_composite)

        # TODO: Find a way to create composite statuses
        # return status_composite

    def energy2(self, E2, wait=False, **kwargs):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parmeters
        ---------
        E2 : float
        	Energy to use for the system.
        """
        # Convert to theta2
        # TODO: Error handling here
        self.theta2 = self.e2_to_theta2(E2)

        # Set the position of the motors on tower 2
        status_t2_th = t2.th.move(-self.theta2, wait=False)
        
        # Set the positions of the motors on tower 3
        status_t3_th = t3.th.move(self.theta2, wait=False)

        # Wait for the status objects to register the moves as complete
        if wait:
            logger.info("Waiting for {} to finish move ...".format(self.name))
            # TODO: Wait on the composite status
            # status_wait(status_composite)        
        
        # TODO: Find a way to create composite statuses
        # return status_composite
        
    def delay(self, t, wait=True, **kwargs):
        """
        Sets the linear stages on the delay line to be the correct length
        according to desired delay and current theta positions.
        
        Parameters
        ----------
        t : float
        	The desired delay from the system.
        """
        self.length = self.t_to_length(t)

        status_t1_l1 = self.t1.l1.move(self.length, wait=False)
        status_t4_l1 = self.t4.l1.move(self.length, wait=False)

        # Wait for the status objects to register the moves as complete
        if wait:
            logger.info("Waiting for {} to finish move ...".format(self.name))
            # TODO: Wait on the composite status
            # status_wait(status_composite)
        
        # TODO: Find a way to create composite statuses
        # return status_composite
        
