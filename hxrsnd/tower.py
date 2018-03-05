"""
Script for the various tower classes.
"""
import logging

import numpy as np
from ophyd import Component as Cmp
from ophyd.status import wait as status_wait

from .snddevice import SndDevice
from .bragg import bragg_angle, bragg_energy
from .attocube import EccBase, TranslationEcc, GoniometerEcc, DiodeEcc
from .aerotech import (AeroBase, RotationAero, InterRotationAero,
                       LinearAero, InterLinearAero)

logger = logging.getLogger(__name__)

class TowerBase(SndDevice):
    """
    Base tower class.
    """
    def __init__(self, prefix, name=None, pos_inserted=None, pos_removed=None, 
                 *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.pos_inserted = pos_inserted
        self.pos_removed = pos_removed
        self.desc_short = "".join([s[0] for s in self.desc.split(" ")])
        
        # Add Tower short name to desc
        for sig_name in self.component_names:
            signal = getattr(self, sig_name)
            if hasattr(signal, "desc"):
                signal.desc = "{0} {1}".format(self.desc_short, signal.desc)
        
    def set_energy(self, E, *args, **kwargs):
        """
        Placeholder for the energy setter. Implement for each TowerBase
        subclass.
        """
        pass

    @property
    def energy(self):
        """
        Returns the energy of the tower according to the angle of the
        arm.

        Returns
        -------
        E : float
            Energy of the delay line.
        """
        # Please forgive me, wasnt having a good day
        return int(np.round(bragg_energy(self.theta)*100))/100

    @energy.setter
    def energy(self, E):
        """
        Sets the theta of the tower to the desired energy. Alias for 
        set_energy(E).

        Parameters
        ----------
        E : float
            Desired energy to set the tower to.
        """
        status = self.set_energy(E)
    
    @property
    def position(self):
        """
        Current position of the tower. Implment this for each TowerBase
        subclass.
        """
        return None

    @property
    def theta(self):
        """
        Bragg angle the tower is currently set to maximize.

        Returns
        -------
        position : float
            Current position of the tower.
        """
        return self.position

    def insert(self, *args, **kwargs):
        """
        Moves the tower x motor to `self.pos_inserted`.

        Returns
        -------
        status : MoveStatus
            Status of the move.

        Raises
        ------
        ValueError
            If pos_inserted is set to None and insert() is called.
        """
        if self.pos_inserted is None:
            raise ValueError("Must set pos_inserted to use insert method.")
        return self.x.move(self.pos_inserted, *args, **kwargs)

    def remove(self, *args, **kwargs):
        """
        Moves the tower x motor to `self.pos_removed`.

        Returns
        -------
        status : MoveStatus
            Status of the move.

        Raises
        ------
        ValueError
            If pos_removed is set to None and remove() is called.
        """
        if self.pos_removed is None:
            raise ValueError("Must set pos_removed to use remove method.")        
        return self.x.move(self.pos_removed, *args, **kwargs)

    @property
    def inserted(self):
        """
        Returns whether the tower is in the inserted position (or close to it).

        Returns
        -------
        inserted : bool
            Whether the tower is inserted or not.

        Raises
        ------
        ValueError
            If pos_inserted is set to None and inserted is called.        
        """
        if self.pos_inserted is None:
            raise ValueError("Must set pos_inserted to check if inserted.")
        return np.isclose(self.pos_inserted, self.position, atol=0.1)

    def _get_move_positions(self, E):
        """
        Returns a list of positions that the energy motors should move to based
        on the inputted theta. Base implementation just returns a list of theta
        with length len(self._energy_motors).

        Parameters
        ----------
        E : float
            Energy to compute the motor move positions for.

        Returns
        -------
        positions : list
            List of positions each of the energy motors need to move to.
        """
        return [bragg_angle(E)] * len(self._energy_motors)

    def check_status(self, energy=None, length=None, no_raise=False):
        """
        Checks to make sure that all the energy motors are not in a bad state. 
        Will include the delay motor if the delay argument is True.

        Parameters
        ----------
        energy : float or None, optional
            Energy to set the tower to.

        length : float or None, optional
            Length to set the delay stage to. (Doesnt apply for cc towers)

        no_raise : bool, optional
            Do not re-raise the attribute error for delay parameters.
        """
        # Create the list of motors and positions we will iterate through
        motors = []
        positions = []

        # Get all the energy parameters
        if energy is not None:
            motors += self._energy_motors
            theta = bragg_angle(energy)
            positions += self._get_move_positions(energy)
            
        # Get the delay parameters
        try:
            if length is not None:
                motors += [self.L]
                positions += length
        except AttributeError:
            if not no_raise:
                raise
        
        # Check that we can move all the motors
        for motor, position in zip(motors, positions):
            try:
                motor.check_status(position)
            except Exception as e:
                err = "Motor {0} got an exception: {1}".format(motor.desc, e)
                logger.error(err)
                raise e

    def stop(self):
        """
        Stops the motions of all the motors.
        """
        self._apply_all("stop", (AeroBase, EccBase), print_set=False)
    
    def enable(self):
        """
        Enables all the aerotech motors.
        """
        self._apply_all("enable", (AeroBase, EccBase), print_set=False)

    def disable(self):
        """
        Disables all the aerotech motors.
        """
        self._apply_all("disable", (AeroBase, EccBase), print_set=False)

    def clear(self):
        """
        Disables all the aerotech motors.
        """
        self._apply_all("clear", AeroBase, print_set=False)

    def status(self, status="", offset=0, print_status=True, newline=False, 
               short=True):
        """
        Returns the status of the tower.
        
        Parameters
        ----------
        status : str, optional
            The string to append the status to.
            
        offset : int, optional
            Amount to offset each line of the status.

        print_status : bool, optional
            Determines whether the string is printed or returned.

        newline : bool, optional
            Adds a new line to the end of the string.

        Returns
        -------
        status : str
            Status string.
        """
        if short:
            # Header
            status += "\n{0}{1}\n{2}{3}".format(
                " "*offset, self.desc, " "*(offset+2), "-"*50)

            # Aerotech body
            status_list_aero = self._apply_all(
                "status", AeroBase, offset=offset+2, print_status=False, 
                short=True)
            if status_list_aero:
                # Aerotech header
                status += "\n{0}{1:<16}|{2:^16}|{3:^16}\n{4}{5}".format(
                    " "*(offset+2), "Motor", "Position", "Dial", " "*(offset+2),
                    "-"*50)
                status += "".join(status_list_aero)

            # Attocube body
            status_list_atto = self._apply_all(
                "status", EccBase, offset=offset+2, print_status=False, 
                short=True)
            if status_list_atto:
                # Attocube Header
                status += "\n{0}{1}\n{2}{3:<16}|{4:^16}|{5:^16}\n{6}{7}".format(
                    " "*(offset+2), "-"*50, " "*(offset+2), "Motor", "Position",
                    "Reference", " "*(offset+2), "-"*50)
                status += "".join(status_list_atto)

        else:
            status += "{0}{1}:\n{2}{3}\n".format(
                " "*offset, self.desc, " "*offset, "-"*(len(self.desc)+1))
            status_list = self._apply_all("status", (AeroBase, EccBase), 
                                          offset=offset+2, print_status=False)
            status += "".join(status_list)

        if newline:
            status += "\n"
        if print_status:
            logger.info(status)
        else:
            return status

        
class DelayTower(TowerBase):
    """
    Delay Tower
    
    Components

    tth : RotationAeroInterlocked
        Rotation axis of the entire delay arm.

    th1 : RotationAero
        Rotation axis of the static crystal.

    th2 : RotationAero
        Rotation axis of the delay crystal.

    x : LinearAero
        Linear stage for insertion/bypass of the tower.

    L : LinearAero
        Linear stage for the delay crystal.

    y1 : TranslationEcc
        Y translation for the static crystal.

    y2 : TranslationEcc
        Y translation for the delay crystal.

    chi1 : GoniometerEcc
        Goniometer on static crystal.

    chi2 : GoniometerEcc
        Goniometer on delay crystal.

    dh : DiodeEcc
        Diode insertion motor.

    diode : HamamatsuDiode
        Diode between the static and delay crystals.

    temp : OmegaRTD
        RTD temperature sensor for the nitrogen.
    """
    # Rotation stages
    tth = Cmp(InterRotationAero, ":TTH", desc="TTH")
    th1 = Cmp(RotationAero, ":TH1", desc="TH1")
    th2 = Cmp(RotationAero, ":TH2", desc="TH2")

    # Linear stages
    x = Cmp(InterLinearAero, ":X", desc="X")
    L = Cmp(InterLinearAero, ":L", desc="L")

    # # Y Crystal motion
    y1 = Cmp(TranslationEcc, ":Y1", desc="Y1")
    y2 = Cmp(TranslationEcc, ":Y2", desc="Y2")

    # Chi motion
    chi1 = Cmp(GoniometerEcc, ":CHI1", desc="CHI1")
    chi2 = Cmp(GoniometerEcc, ":CHI2", desc="CHI2")

    # Diode motion
    dh = Cmp(DiodeEcc, ":DH", desc="DH")
    
    # # Diode
    # diode = Cmp(HamamatsuDiode, ":DIODE", desc="Tower Diode")

    # # Temperature monitor
    # temp = Cmp(OmegaRTD, ":TEMP", desc="Tower RTD")
    
    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self._energy_motors = [self.tth, self.th1, self.th2]

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

    def _get_move_positions(self, E):
        """
        Returns the list of positions that each of the energy motors need to
        move to based on the inputted theta. tth moves to 2*theta while all
        the other motors move to theta.

        Parameters
        ----------
        E : float
            Energy to compute the motor move positions for.

        Returns
        -------
        positions : list
            List of positions each of the energy motors need to move to.
        """
        # Convert to theta
        theta = bragg_angle(E=E)

        # Get the positions
        positions = []
        for motor in self._energy_motors:
            if motor is self.tth:
                positions.append(2*theta)
            else:
                positions.append(theta)
        return positions

    def set_energy(self, E, wait=False, check_status=True):
        """
        Sets the angles of the crystals in the delay line to maximize the
        inputted energy.        
    
        Parameters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for each motor to complete the motion.

        check_status : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Check to make sure the motors are in a valid state to move
        if check_status:
            self.check_status(energy=E)
        
        # Perform the move
        status = [motor.move(pos, wait=False, check_status=False) for
                  motor, pos in zip(self._energy_motors, 
                                    self._get_move_positions(E))]

        # Wait for the motions to finish
        if wait:
            for s in status:
                logger.info("Waiting for {} to finish move ...".format(
                    s.device.name))
                status_wait(s)
                
        return status

    def set_length(self, position, wait=False, *args, **kwargs):
        """
        Sets the position of the linear delay stage in mm.

        Parameters
        ----------
        position : float
            Position to move the delay motor to.

        wait : bool, optional
            Wait for motion to complete before returning the console.

        Returns
        -------
        status : MoveStatus
            Status object of the move.
        """
        return self.L.move(position, wait=wait, *args, **kwargs)

    @property
    def length(self):
        """
        Returns the position of the linear delay stage (L) in mm.

        Returns
        -------
        position : float
            Position in mm of the linear delay stage.
        """
        return self.L.position

    @length.setter
    def length(self, position):
        """
        Sets the position of the linear delay stage in mm.

        Parameters
        ----------
        position : float
            Position to move the delay motor to.
        """
        status = self.L.mv(position)

    @property
    def theta(self):
        """
        Bragg angle the tower is currently set to maximize.

        Returns
        -------
        position : float
            Current position of the tower.
        """
        return self.position/2    
        

class ChannelCutTower(TowerBase):
    """
    Channel Cut tower.

    Components

    th : RotationAero
        Rotation stage of the channel cut crystal

    x : LinearAero
        Translation stage of the tower
    """
    # Rotation
    th = Cmp(RotationAero, ":TH", desc="TH")

    # Translation
    x = Cmp(LinearAero, ":X", desc="X")

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self._energy_motors = [self.th]

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

    def set_energy(self, E, wait=False, check_status=True):
        """
        Sets the angles of the crystals in the channel cut line to maximize the
        inputted energy.        
    
        Parameters
        ---------
        E : float
            Energy to use for the system.

        wait : bool, optional
            Wait for motion to complete before returning the console.

        check_status : bool, optional
            Check if the motors are in a valid state to move.
        """
        # Convert to theta
        theta = bragg_angle(E=E)
        
        # Check to make sure the motors are in a valid state to move
        if check_status:
            self.check_status(E)

        # Perform the move
        status = self.th.move(theta, wait=wait)
        return status
