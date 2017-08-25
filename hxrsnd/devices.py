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
from ophyd.utils.epics_pvs import raise_if_disconnected
from ophyd.status import wait as status_wait

########
# SLAC #
########
from pcdsdevices.device import Device
from pcdsdevices.epics.attocube import EccMotor
from pcdsdevices.epics.aerotech import AeroBase

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
    """
    pass


class ChannelCutTower(TowerBase):
    """
    Channel Cut tower.
    """
    pass


class SnD(Device):
    """
    Hard X-Ray Split and Delay System.
    """
    t1 = component(DelayTower, ":T1")
    t1 = component(ChannelCutTower, ":T2")
    t1 = component(ChannelCutTower, ":T3")
    t4 = component(DelayTower, ":T4")

    # Constants
    c = 299792458               # m/s

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
        theta1 = self.e1_to_theta1(E1)

        # Set the position of the motors on tower 1
        status_t1_th1 = t1.th1.move(theta1, wait=wait)
        status_t1_th2 = t1.th2.move(theta1, wait=wait)
        status_t1_thh = t1.tth.move(2*theta1, wait=wait)

        # Set the positions of the motors on tower 4
        status_t4_th1 = t4.th1.move(theta1, wait=wait)
        status_t4_th2 = t4.th2.move(theta1, wait=wait)
        status_t4_thh = t4.tth.move(2*theta1, wait=wait)

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
        theta2 = self.e2_to_theta2(E2)

        # Set the position of the motors on tower 2
        status_t2_th = t2.th.move(-theta2, wait=wait)
        
        # Set the positions of the motors on tower 3
        status_t3_th = t3.th.move(theta2, wait=wait)
        
        # TODO: Find a way to create composite statuses
        # return status_composite
        
    # def delay(self, t, **kwargs):
    #     """
    #     Sets the linear stages on the
        
        
