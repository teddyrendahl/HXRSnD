"""
Script to hold the energy macromotors

All units of time are in picoseconds, units of length are in mm.
"""
import time
import logging
from functools import reduce

import pandas as pd
from ophyd.device import Component as Cmp
from ophyd.utils import LimitError
from ophyd.status import wait as status_wait
from bluesky.preprocessors  import run_wrapper

from pswalker.utils import field_prepend

from .sndmotor import SndMotor
from .snddevice import SndDevice
from .detectors import OpalDetector
from .utils import as_list, flatten, PythonSignal
from .bragg import bragg_angle, cosd, sind
from .exceptions import (MotorDisabled, MotorFaulted, MotorStopped, 
                         BadN2Pressure, InputError)
from .plans.calibration import calibrate_motor
from .plans.preprocessors import return_to_initial

logger = logging.getLogger(__name__)

# TODO: Add a calibrate method
# TODO: Add a centroid scanning method
# TODO: Add has_calib and use_calib attributes
# TODO: Add ability to save caibrations to disk
# TODO: Add ability to load calibrations from disk
# TODO: Add ability to display calibrations
# TODO: Add ability to change post-processing done to scan. 
# TODO : Add ability to redo scaling on scan
class CalibMacro(SndDevice):
    """
    Provides the calibration macro methods.
    """
    def __init__(self, prefix, name=None, calib_detector=None, 
                 calib_motors=None, calib_fields=None, motor_fields=None, 
                 *args, **kwargs):

        super().__init__(prefix, name=name, *args, **kwargs)
        self.calib_motors = calib_motors
        self.calib_fields = calib_fields
        self.motor_fields = motor_fields
        self.use_calib = False
        self._calib = {}
        self.configure()

    def move(self, position, wait=False, use_calib=True, *args, **kwargs):
        """
        Move that performs the additional calibration move.
        """
        status = super().move(position, wait=False, *args, **kwargs)
        
        # Perform the calibration move
        if use_calib and self._has_calib:
            status = status & self._calib_compensate(position)
            
        # Wait for all the motors to finish moving
        if wait:
            self.wait(status)

        return status

    def calibrate(self, start, stop, steps, average=100, confirm_overwrite=True,
                  detector=None, detector_fields=None, RE=None, *args, **kwargs):
        """
        Performs a calibration scan for this motor and updates the 
        configuration.
        """
        # Use the inputted runengine or the parent's
        RE = RE or self.parent._RE
        detector = detector or self.calib_detector
        detector_fields = detector_fields or self.detector_fields

        # Make sure everything returns to the starting position when finished
        @return_to_initial(self, *self.calib_motors)
        def inner():
            yield from calibrate_motor(
                detector, 
                self, 
                self.motor_fields,
                self.calib_motors,
                start, stop, steps,
                average=average,
                detector_fields=detector_fields,
                calib_fields=self.calib_fields,
                confirm_overwrite=confirm_overwrite,
                return_to_start=False,
                *args, **kwargs)
            
        # Run the inner plan
        RE(run_wrapper(inner()))

    def configure(self, *, calib=None, motors=None, scan=None, scale=None, 
                  start=None):
        """
        Configure the macro-motor's move parameters.

        Parameters
        ----------
        calib : DataFrame or dict, optional
            Lookup table for move calibration. This represents set positions of
            auxiliary movers that should be chosen as we move our main macro.
        Returns
        -------
        configs : tuple of dict
            old_config, new_config
        """
        # Save prev for return statement
        prev_config = self.read_configuration()
        self._config_calib(calib, motors, scan, scale, start)

        # If we get a good calibration, change use_calib so we can use it
        if self.has_calib:
            self.use_calib = True

        # Return the previous and new configs
        return prev_config, self.read_configuration()

    def _config_calib(self, calib, motors, scan, scale, start):
        """
        Handle calib arg from configure
        """
        # Start with all the previous calibration parameters
        save_calib = dict(self._calib)
        motors = as_list(motors) or None

        # Add in the new parameters if they are not None or empty. If they are,
        # None or empty, check if they already exist as keys in the dict and 
        # only add them if they do not.
        for key, value in {'calib': calib, 'motors': motors, 'scan': scan, 
                           'scale': scale, 'start': start}.items():
            if value is not None or (value is None and key not in save_calib):
                save_calib[key] = {'value': value, 'timestamp': time.time()}
                
        # Now check all those changes, raising errors if needed
        self._check_calib(save_calib)
        # We made it through the check, therefore it is safe to use
        self._calib = save_calib

    def _check_calib(self, save_calib):
        # Let's get all the values we will update the calibration with
        calib = save_calib['calib']['value']
        motors = save_calib['motors']['value']
        scan = save_calib['scan']['value']
        scale = save_calib['scale']['value']
        start = save_calib['start']['value']

        # Having no correction table and no calibration motors is valid
        if calib is None and not motors:
            pass

        # We have no calibration but calibration motors.
        elif calib is None and motors:
            raise InputError("Adding motors for calibration but no correction "
                             "table found.")

        # We have a correction table but it isnt a Dataframe
        elif not isinstance(calib, pd.DataFrame):
            raise TypeError("Only Dataframes are supported for calibrations "
                            "tables at this time. Got a calibration of type "
                            "{0}.".format(type(calib)))

        # We have a correction table but no motors to correct with
        elif calib is not None and not motors:
            raise InputError("Adding a correction table with no calibration "
                             "motors")

        # We have a correction table and calibration motors, but they arent the
        # same length, so we cannot actually use it
        elif len(calib.columns) != len(motors):
            raise InputError("Mismatched calibration size and number of "
                             "motors. Got {0} columns for {1} motors.".format(
                                len(calib.columns),len(motors)))

        # We have the correct correction table and motors but one of the of the
        # extra parameters were not passed. Not crutial but should warn the user
        elif calib is not None and motors and not (scan or scale or start):
            logger.warning("Inputted correction table and calibration motors "
                           "but not all configuration data. Some calibration "
                           "updating methods may not be functional!")

    def _calib_compensate(self, position, *args, **kwargs):
        """
        Do the calib adjust move
        """
        calib = self._calib['calib']['value']
        motors = self._calib['motors']['value']
        status_list = []

        if not self.has_calib or not self.use_calib:
            return 
        # Grab the two rows where the main motor position (column 0) is
        # closest to the inputted position
        top = calib.iloc[(calib.iloc[:,0] - position).abs().argsort().iloc[:2]]
        first, second = top.iloc[0], top.iloc[1]

        # Get the slope between the lines between each of the motor values using
        # the first column as the x positions
        slopes = (second - first) / (second.iloc[0] - first.iloc[1])

        # Use the slope and the closest point to interpolate the motor positions
        # at the inputted position
        interpolated_row = slopes * (position - first[0]) + first

        # Move each calibration motor to the interpolated position
        for i, motor in enumerate(motors[1:]):
            status = motor.move(interpolated_row[i+1], *args, **kwargs)
            status_list.append(status)

        # Turn all the status objects into one AndStatus and return it
        return reduce(lambda x, y: x & y, status_list)

    @property
    def has_calib(self):
        config = self._calib
        calib = config['calib']['value']
        motors = config['motors']['value']
        # Return False if we dont have a table and motors
        if calib is not None and not motors:
            return False
        try:
            # If we make it through the check, we have a calibration
            self._check_calib(config)
            return True
        except:
            # We ran into an error in the check, the config is somehow invalid
            return False

    @property
    def use_calib(self):
        return self._use_calib
    
    @use_calib.setter
    def use_calib(self, use):
        self._use_calib = bool(use)
        if self._use_calib is True and not self.has_calib:
            logger.warning("use_calib is currently set to True but the "
                           "current calibration is not valid.")
    
    def read_configuration(self):
        return self._calib

    def describe_configuration(self):
        if not self._calib:
            return super().describe_configuration()
        if isinstance(self._calib['calib']['value'], pd.DataFrame):
            shape = self._calib['calib']['value'].shape
        else:
            shape = [len(self._calib)]
        return {**dict(calib=dict(source='calibrate', dtype='array', 
                                  shape=shape)), 
                **super().describe_configuration()}


class MacroBase(SndMotor):
    """
    Base pseudo-motor class for the SnD macro-motions.
    """
    # Constants
    c = 0.299792458             # mm/ps
    gap = 55                    # m

    readback = Cmp(PythonSignal, lambda : None)

    def __init__(self, prefix, name=None, read_attrs=None, *args, **kwargs):
        read_attrs = read_attrs or ["readback"]
        super().__init__(prefix, name=name, read_attrs=read_attrs, *args, 
                         **kwargs)
        self.readback._func = lambda : self.position

        # Make sure this is used
        if self.parent is None:
            logger.warning("Macromotors must be instantiated with a parent "
                           "that has the SnD towers as components to function "
                           "properly.")
        else:
            self._delay_towers = [self.parent.t1, self.parent.t4]
            self._channelcut_towers = [self.parent.t2, self.parent.t3]

    @property
    def position(self):
        """
        Returns the current position
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return (self.parent.t1.energy, self.parent.t2.energy,
                self._length_to_delay())

    def _verify_move(self, *args, **kwargs):
        """
        Prints a summary of the current positions and the proposed positions
        of the motors based on the inputs. It then prompts the user to confirm
        the move. To be overrided in subclasses.
        """
        pass

    def _check_towers_and_diagnostics(self, *args, **kwargs):
        """
        Checks the towers in the delay line and the channel cut line to make 
        sure they can be moved. Depending on if E1, E2 or delay are entered, 
        the delay line energy motors, channel cut line energy motors or the 
        delay stages will be checked for faults, if they are enabled, if the
        requested energy requires moving beyond the limits and if the pressure
        in the tower N2 is good. To be overrided in subclasses.
        """
        pass

    def _move_towers_and_diagnostics(self, *args, **kwargs):
        """
        Moves all the tower and diagnostic motors according to the inputted
        energies and delay. If any of the inputted information is set to None
        then that component of the move is ignored. To be overrided in 
        subclasses.
        """
        pass

    def _add_verify_header(self, string=""):
        """
        Adds the header that labels the motor desc, current position and propsed
        position.

        Parameters
        ----------
        string : str
            String to add a header to.

        Returns
        -------
        string : str
            String with the header added to it.
        """
        header = "\n{:^15}|{:^15}|{:^15}".format("Motor", "Current", "Proposed")
        header += "\n" + "-"*len(header)
        return string + header

    def wait(self, status=None):
        """
        Waits for the status objects to complete the motions.
        
        Parameters
        ----------
        status : list or None, optional
            List of status objects to wait on. If None, will wait on the
            internal status list.
        """
        status = status or self._status
        logger.info("Waiting for the motors to finish moving...")
        for s in list(status):
            status_wait(s)
        logger.info("Move completed.")

    def set(self, position, wait=True, verify_move=True, ret_status=True, 
            use_diag=True, use_calib=True):
        """
        Moves the macro-motor to the inputted position, optionally waiting for
        the motors to complete their moves.

        Parameters
        ----------
        position : float
            Position to move the macro-motor to.
        
        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.

        use_calib : bool, optional
            Use the configurated calibration parameters
        
        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        return self.move(position, wait=wait, verify_move=verify_move,
                         ret_status=ret_status, use_diag=use_diag,
                         use_calib=use_calib)

    def move(self, position, wait=True, verify_move=True, use_diag=True):
        """
        Moves the macro-motor to the inputted position, optionally waiting for
        the motors to complete their moves. Alias for set().

        Parameters
        ----------
        position : float
            Position to move the macro-motor to.
        
        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.
        
        use_diag : bool, optional
            Move the daignostic motors to align with the beam.

        use_calib : bool, optional
            Use the configurated calibration parameters
        
        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        # Check the towers and diagnostics
        diag_pos = self._check_towers_and_diagnostics(position, 
                                                      use_diag=use_diag)

        # Prompt the user about the move before making it
        if verify_move and self._verify_move(position, use_diag=use_diag):
            return

        # Send the move commands to all the motors
        status_list = flatten(self._move_towers_and_diagnostics(
            position, diag_pos, use_diag=use_diag))

        # Aggregate the status objects
        status = reduce(lambda x, y: x & y, status_list)

        # Wait for all the motors to finish moving
        if wait:
            self.wait(status)
            
        return status

    def mv(self, position, wait=True, verify_move=True, use_diag=True, *args, 
           **kwargs):
        """
        Moves the macro parameters to the inputted positions. For energy, this 
        moves the energies of both lines, energy1 moves just the delay line, 
        energy2 moves just the channel cut line, and delay moves just the delay 
        motors.
        
        mv() is different from move() by catching all the common exceptions that
        this motor can raise and just raises a logger warning. Therefore if 
        building higher level functionality, do not use this method and use 
        move() instead, otherwise none of the exceptions will propagate beyond
        this method.

        Parameters
        ----------
        position : float
            Position to move the motor to.

        wait : bool, optional
            Wait for each motor to complete the motion before returning the
            console.
            
        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        ret_status : bool, optional
            Return the status object of the move.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        
        Exceptions Caught
        -----------------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        status : list
            List of status objects for each motor that was involved in the move.
        """
        try:
            return super().mv(position, wait=wait, verify_move=verify_move, 
                              use_diag=use_diag, *args, **kwargs)
        # Catch all the common motor exceptions        
        except LimitError:
            logger.warning("Requested move is outside the soft limits")
        except MotorDisabled:
            logger.warning("Cannot move '{0}' - a motor is currently disabled. "
                           "Try running 'motor.enable()'.".format(self.desc))
        except MotorFaulted:
            logger.warning("Cannot move '{0}' - a motor is currently faulted. "
                           "Try running 'motor.clear()'.".format(self.desc))
        except MotorStopped:
            logger.warning("Cannot move '{0}' - a motor is currently stopped. "
                           "Try running 'motor.state='Go''.".format(self.desc))
        except BadN2Pressure:
            logger.warning("Cannot move '{0}' - pressure in a tower is bad."
                           "".format(self.desc))

    def set_position(self, *args, **kwargs):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay. To be 
        overrided in subclasses.
        """
        pass

    @property
    def aligned(self, *args, **kwargs):
        """
        Checks to see if the towers are in aligned in energy and delay. To be 
        overrided in subclasses.
        """
        pass

    def _confirm_move(self, string):
        """
        Performs a basic confirmation of the move.

        Parameters
        ----------
        string : str
            Message to be printed to user.
        """
        logger.info(string)
        try:
            response = input("\nConfirm Move [y/n]: ")
        except Exception as e:
            logger.info("Exception raised: {0}".format(e))
            response = "n"

        if response.lower() != "y":
            logger.info("\nMove cancelled.")
            return True
        else:
            logger.debug("\nMove confirmed.")
            return False        
            
    def status(self, status="", offset=0, print_status=True, newline=False):
        """
        Returns the status of the device.
        
        Parameters
        ----------
        status : str, optional
            The string to append the status to.
            
        offset : int, optional
            Amount to offset each line of the status.

        print_status : bool, optional
            Determines whether the string is printed or returned.
        """
        try:
            status += "\n{0}{1:<16} {2:^16}".format(
                " "*offset, self.desc+":", self.position)
        except TypeError:
            status += "\n{0}{1:<16} {2:^}".format(
                " "*offset, self.desc+":", str(self.position))

        if newline:
            status += "\n"
        if print_status:
            logger.info(status)
        else:
            return status        
        
    def __repr__(self):
        """
        Returns the status of the motor. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        return self.status(print_status=False)


class DelayTowerMacro(MacroBase):
    """
    Class for the delay tower macros
    """
    def _delay_to_length(self, delay, theta1=None, theta2=None):
        """
        Converts the inputted delay to the lengths on the delay arm linear
        stages.

        Parameters
        ----------
        delay : float
            The desired delay in picoseconds.

        theta1 : float or None, optional
            Bragg angle the delay line is set to maximize.

        theta2 : float or None, optional
            Bragg angle the channel cut line is set to maximize.

        Returns
        -------
        length : float
            The distance between the delay crystal and the splitting or
            recombining crystal.
        """
        # Check if any other inputs were used
        theta1 = theta1 or self.parent.theta1
        theta2 = theta2 or self.parent.theta2

        # Length calculation
        length = ((delay*self.c/2 + self.gap*(1 - cosd(2*theta2)) /
                   sind(theta2)) / (1 - cosd(2*theta1)))
        return length

    def _get_delay_diagnostic_position(self, E1=None, E2=None, delay=None):
        """
        Gets the position the delay diagnostic needs to move to based on the 
        inputted energies and delay or the current bragg angles and current 
        delay of the system.

        Parameters
        ----------
        E1 : float or None, optional
            Energy in eV to use for the delay line. Uses the current energy if 
            None is inputted.

        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current 
            energy if None is inputted.
        
        delay : float or None, optional
            Delay in picoseconds to use for the calculation. Uses current delay
            if None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the 
            inputted parameters.
        """
        # Use current bragg angle
        if E1 is None:
            theta1 = self.parent.theta1
        else:
            theta1 = bragg_angle(E=E1)

        # Use current delay stage position if no delay is inputted
        if delay is None:
            length = self.parent.t1.length
        # Calculate the expected delay position if a delay is inputted
        else:
            if E2 is None:
                theta2 = self.parent.theta2
            else:
                theta2 = bragg_angle(E=E2)
            length = self._delay_to_length(delay, theta1=theta1, theta2=theta2)
            
        # Calculate position the diagnostic needs to move to
        position = -length*sind(2*theta1)
        return position
    

class DelayMacro(CalibMacro, DelayTowerMacro):
    """
    Macro-motor for the delay macro-motor.
    """
    # @property
    # def aligned(self, rtol=0, atol=0.001):
    #     """
    #     Checks to see if the towers are in aligned in energy and delay.

    #     Parameters
    #     ----------
    #     rtol : float, optional
    #         Relative tolerance to use when comparing value differences.
        
    #     atol : float, optional
    #         Absolute tolerance to use when comparing value differences.

    #     Returns
    #     -------
    #     is_aligned : bool
    #         True if the towers are aligned, False if not.
    #     """
    #     t1_delay = self._length_to_delay(self.parent.t1.length)
    #     t4_delay = self._length_to_delay(self.parent.t4.length)
    #     is_aligned = np.isclose(t1_delay, t4_delay, atol=atol, rtol=rtol)
    #     if not is_aligned:
    #         logger.warning("Delay mismatch between t1 and t4. t1: {0:.3f}ps, "
    #                        "t4: {1:.3f}ps".format(t1_delay, t4_delay))
    #     return is_aligned

    def __init__(self, prefix, name=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)

        self.calib_motors=[self.parent.t1.chi1, self.parent.t1.y1]
        self.calib_fields=[field_prepend("user_readback", calib_motor)
                           for calib_motors in self.calib_motors]
        self.calib_detector=OpalDetector("XCS:USR:O1000:01", name="Opal 1")
        self.detector_fields=['stats2_centroid_x', 'stats2_centroid_y',]

    def _length_to_delay(self, L=None, theta1=None, theta2=None):
        """
        Converts the inputted L of the delay stage, theta1 and theta2 to
        the expected delay of the system, or uses the current positions
        as inputs.

        Parameters
        ----------
        L : float or None, optional
            Position of the linear delay stage.
        
        theta1 : float or None, optional
            Bragg angle the delay line is set to maximize.

        theta2 : float or None, optional
            Bragg angle the channel cut line is set to maximize.

        Returns
        -------
        delay : float
            The delay of the system in picoseconds.
        """
        # Check if any other inputs were used
        L = L or self.parent.t1.length
        theta1 = theta1 or self.parent.theta1
        theta2 = theta2 or self.parent.theta2

        # Delay calculation
        delay = (2*(L*(1 - cosd(2*theta1)) - self.gap*(1 - cosd(2*theta2)) /
                    sind(theta2))/self.c)
        return delay

    def _verify_move(self, delay, string="", use_header=True, confirm_move=True,
                     use_diag=True):
        """
        Prints a summary of the current positions and the proposed positions
        of the delay motors based on the inputs. It then prompts the user to 
        confirm the move.
        
        Parameters
        ----------
        delay : float
            Desired delay of the system.

        string : str, optional
            Message to be printed as a prompt.

        use_header : bool, optional
            Adds a basic header to the message.

        confirm_move : bool, optional
            Prompts the user for confirmation.

        use_diag : bool, optional
            Add the diagnostic motor to the list of motors to verify.
        
        Returns
        -------
        allowed : bool
            True if the move is approved, False if the move is not.
        """
        # Add a header to the output
        if use_header:
            string += self._add_verify_header(string)

        # Convert to length and add the body of the string
        length = self._delay_to_length(delay)
        for tower in self._delay_towers:
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                tower.L.desc, tower.length, length)

        # Add the diagnostic move
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(delay=delay)
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                self.parent.dd.x.desc, self.parent.dd.x.position, position_dd)

        # Prompt the user for a confirmation or return the string
        if confirm_move is True:
            return self._confirm_move(string)
        else:
            return string

    def _check_towers_and_diagnostics(self, delay, use_diag=True):
        """
        Checks the staus of the delay stages on the delay towers. Raises the 
        basic motor errors if any of the motors are not ready to be moved.
        
        Parameters
        ----------
        delay : float
            The desired delay of the system.

        use_diag : bool, optional
            Check the position of the diagnostic motor.
        
        Raises
        ------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        position_dd : list
            Position to move the delay diagnostic to.
        """
        # Get the desired length for the delay stage
        length = self._delay_to_length(delay)

        # Check each of the delay towers
        for tower in self._delay_towers:
            tower.check_status(length=length)

        if use_diag:
            # Check the delay diagnostic position
            position_dd = self._get_delay_diagnostic_position(delay=delay)
            self.parent.dd.x.check_status(position_dd)
            return position_dd

    def _move_towers_and_diagnostics(self, delay, position_dd, use_diag=True):
        """
        Moves the delay stages and delay diagnostic according to the inputted
        delay and diagnostic position.
        
        Parameters
        ----------
        delay  : float
            Delay to set the system to.

        position_dd : float
            Position to move the delay diagnostic to.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        
        Returns
        -------
        status : list
            Nested list of status objects from each tower.
        """            
        # Get the desired length for the delay stage
        length = self._delay_to_length(delay)

        # Move the delay stages
        status = [tower.set_length(length, wait=False, check_status=False) 
                   for tower in self._delay_towers]
        # Log the delay change
        logger.debug("Setting delay to {0}.".format(delay))
        
        if use_diag:
            # Move the delay diagnostic to the inputted position
            status += [self.parent.dd.x.move(position_dd, wait=False)]

        return status        

    @property
    def position(self):
        """
        Returns the current energy of the channel cut line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self._length_to_delay()
    
    def set_position(self, delay=None, print_set=True, use_diag=True,
                     verify_move=True):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay.
        
        Parameters
        ----------
        delay : float or None, optional
            Delay to set the delay stages to.
        
        print_set : bool, optional
            Print a message to the console that the set has been made.

        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.
        """            
        # Prompt the user about the move before making it
        if verify_move and self._verify_move(delay, use_diag=use_diag):
            return

        length = self._delay_to_length(delay)
        
        # Set the position of each delay stage
        for tower in self._delay_towers:
            tower.L.set_position(length, print_set=False)
                
        # Diagnostic
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(delay=delay)
            self.parent.dd.x.set_position(position_dd, print_set=False)            

        if print_set:
            logger.info("Setting positions for delay to {0}.".format(delay))


class Energy1Macro(DelayTowerMacro):
    """
    Macro-motor for the energy 1 macro-motor.
    """
    # @property
    # def aligned(self, rtol=0, atol=0.001):
    #     """
    #     Checks to see if the towers are in aligned in energy and delay.

    #     Parameters
    #     ----------
    #     rtol : float, optional
    #         Relative tolerance to use when comparing value differences.
        
    #     atol : float, optional
    #         Absolute tolerance to use when comparing value differences.

    #     Returns
    #     -------
    #     is_aligned : bool
    #         True if the towers are aligned, False if not.
    #     """
    #     t1 = self.parent.t1
    #     t4 = self.parent.t4
    #     is_aligned = np.isclose(t1.energy, t4.energy, atol=atol, rtol=rtol)
    #     if not is_aligned:
    #         logger.warning("Energy mismatch between t1 and t4. t1: {0:.3f}  eV,"
    #                        " t4: {1:.3f} eV".format(t1.energy, t4.energy))                        
    #     return is_aligned

    def _length_to_delay(self, L=None, theta1=None, theta2=None):
        """
        Converts the inputted L of the delay stage, theta1 and theta2 to
        the expected delay of the system, or uses the current positions
        as inputs.

        Parameters
        ----------
        L : float or None, optional
            Position of the linear delay stage.
        
        theta1 : float or None, optional
            Bragg angle the delay line is set to maximize.

        theta2 : float or None, optional
            Bragg angle the channel cut line is set to maximize.

        Returns
        -------
        delay : float
            The delay of the system in picoseconds.
        """
        # Check if any other inputs were used
        L = L or self.parent.t1.length
        theta1 = theta1 or self.parent.theta1
        theta2 = theta2 or self.parent.theta2

        # Delay calculation
        delay = (2*(L*(1 - cosd(2*theta1)) - self.gap*(1 - cosd(2*theta2)) /
                    sind(theta2))/self.c)
        return delay

    def _verify_move(self, E1, string="", use_header=True, confirm_move=True,
                     use_diag=True):
        """
        Prints a summary of the current positions and the proposed positions
        of the motors based on the inputs. It then prompts the user to confirm
        the move.
        
        Parameters
        ----------
        E1 : float
            Desired energy for the delay line.

        string : str, optional
            Message to be printed as a prompt.

        use_header : bool, optional
            Adds a basic header to the message.

        confirm_move : bool, optional
            Prompts the user for confirmation.

        use_diag : bool, optional
            Add the diagnostic motor to the list of motors to verify.
        
        Returns
        -------
        allowed : bool
            True if the move is approved, False if the move is not.
        """
        # Add a header to the output
        if use_header:
            string += self._add_verify_header(string)

        # Get move for each motor in the delay towers
        for tower in self._delay_towers:
            for motor, position in zip(tower._energy_motors,
                                       tower._get_move_positions(E1)):
                string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                    motor.desc, motor.position, position)

        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1)
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                self.parent.dd.x.desc, self.parent.dd.x.position, position_dd)

        # Prompt the user for a confirmation or return the string
        if confirm_move is True:
            return self._confirm_move(string)
        else:
            return string

    def _check_towers_and_diagnostics(self, E1, use_diag=True):
        """
        Checks the staus of the delay tower energy motors. Raises the basic 
        motor errors if any of the motors are not ready to be moved
        
        Parameters
        ----------
        E1 : float
            Desired energy for the delay line.

        use_diag : bool, optional
            Check the position of the diagnostic motor.
        
        Raises
        ------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        position_dd : float or None
            Position to move the delay diagnostic to.
        """
        # Check each of the delay towers
        for tower in self._delay_towers:
            tower.check_status(energy=E1)

        # Check the delay diagnostic position
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1=E1)
            self.parent.dd.x.check_status(position_dd)
            return position_dd

    def _move_towers_and_diagnostics(self, E1, position_dd, use_diag=True):
        """
        Moves the delay line energy motors and diagnostic to the inputted energy
        and diagnostic position.
        
        Parameters
        ----------
        E1 : float
            Energy to set the delay line to.
        
        position_dd : float
            Position to move the delay diagnostic to.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        
        Returns
        -------
        status : list
            Nested list of status objects from each tower.
        """
        # Move the towers to the specified energy
        status = [tower.set_energy(E1, wait=False, check_status=False) for
                   tower in self._delay_towers]
        # Log the energy change
        logger.debug("Setting E1 to {0}.".format(E1))

        # Move the delay diagnostic to the inputted position
        if use_diag:
            status += [self.parent.dd.x.move(position_dd, wait=False)]

        return status

    def _get_delay_diagnostic_position(self, E1=None):
        """
        Gets the position the delay diagnostic needs to move to based on the 
        inputted energies and delay or the current bragg angles and current 
        delay of the system.

        Parameters
        ----------
        E1 : float or None, optional
            Energy in eV to use for the delay line. Uses the current energy if 
            None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the 
            inputted parameters.
        """
        return super()._get_delay_diagnostic_position(E1=E1)

    @property
    def position(self):
        """
        Returns the current energy of the delay line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self.parent.t1.energy

    def set_position(self, E1=None, print_set=True, verify_move=True,
                     use_diag=True):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay.
        
        Parameters
        ----------
        E1 : float or None, optional
            Energy to set the delay line to.
        
        print_set : bool, optional
            Print a message to the console that the set has been made.

        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        """
        # Prompt the user about the move before making it
        if verify_move and self._verify_move(E1, use_diag=use_diag):
            return

        # Set position of each E1 motor in each delay tower
        for tower in self._delay_towers:
            for motor, pos in zip(tower._energy_motors,
                                  tower._get_move_positions(E1)):
                motor.set_position(pos, print_set=False)

        # Set the diagnostic
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1=E1)
            self.parent.dd.x.set_position(position_dd, print_set=False)

        # Log the set
        if print_set is True:
            logger.info("Setting positions for E1 to {0}.".format(E1))


class Energy1CCMacro(Energy1Macro):
    """
    Macro-motor for the energy 1 channel cut macro-motor.
    """
    def _verify_move(self, E1, string="", use_header=True, confirm_move=True,
                     use_diag=True):
        """
        Prints a summary of the current positions and the proposed positions
        of the motors based on the inputs. It then prompts the user to confirm
        the move.
        
        Parameters
        ----------
        E1 : float
            Desired energy for the delay line.

        string : str, optional
            Message to be printed as a prompt.

        use_header : bool, optional
            Adds a basic header to the message.

        confirm_move : bool, optional
            Prompts the user for confirmation.

        use_diag : bool, optional
            Add the diagnostic motor to the list of motors to verify.
        
        Returns
        -------
        allowed : bool
            True if the move is approved, False if the move is not.
        """
        # Add a header to the output
        if use_header:
            string += self._add_verify_header(string)

        # Get move for each motor in the delay towers
        for tower in self._delay_towers:
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                    tower.tth.desc, tower.tth.position, 2*bragg_angle(E1))

        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1)
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                self.parent.dd.x.desc, self.parent.dd.x.position, position_dd)

        # Prompt the user for a confirmation or return the string
        if confirm_move is True:
            return self._confirm_move(string)
        else:
            return string

    def _check_towers_and_diagnostics(self, E1, use_diag=True):
        """
        Checks the staus of the delay tower energy motors. Raises the basic 
        motor errors if any of the motors are not ready to be moved
        
        Parameters
        ----------
        E1 : float
            Desired energy for the delay line.

        use_diag : bool, optional
            Check the position of the diagnostic motor.
        
        Raises
        ------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        position_dd : float or None
            Position to move the delay diagnostic to.
        """
        # Check each of the delay towers
        for tower in self._delay_towers:
            tower.tth.check_status(2*bragg_angle(E1))

        # Check the delay diagnostic position
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1=E1)
            self.parent.dd.x.check_status(position_dd)
            return position_dd

    def _move_towers_and_diagnostics(self, E1, position_dd, use_diag=True):
        """
        Moves the delay line energy motors and diagnostic to the inputted energy
        and diagnostic position.
        
        Parameters
        ----------
        E1 : float
            Energy to set the delay line to.
        
        position_dd : float
            Position to move the delay diagnostic to.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        
        Returns
        -------
        status : list
            Nested list of status objects from each tower.
        """
        # Move the towers to the specified energy
        status = [tower.tth.move(2*bragg_angle(E1), wait=False, 
                                 check_status=False)
                  for tower in self._delay_towers]
        # Log the energy change
        logger.debug("Setting E1_cc to {0}.".format(E1))

        # Move the delay diagnostic to the inputted position
        if use_diag:
            status += [self.parent.dd.x.move(position_dd, wait=False)]

        return status

    def set_position(self, E1=None, print_set=True, verify_move=True,
                     use_diag=True):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay.
        
        Parameters
        ----------
        E1 : float or None, optional
            Energy to set the delay line to.
        
        print_set : bool, optional
            Print a message to the console that the set has been made.

        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        """
        # Prompt the user about the move before making it
        if verify_move and self._verify_move(E1, use_diag=use_diag):
            return

        # Set position of each E1 motor in each delay tower
        for tower in self._delay_towers:
            tower.tth.set_position(2*bragg_angle(E1), print_set=False)

        # Set the diagnostic
        if use_diag:
            position_dd = self._get_delay_diagnostic_position(E1=E1)
            self.parent.dd.x.set_position(position_dd, print_set=False)

        # Log the set
        if print_set is True:
            logger.info("Setting positions for E1 to {0}.".format(E1))


class Energy2Macro(MacroBase):
    """
    Macro-motor for the energy 2 macro-motor.
    """
    def _get_channelcut_diagnostic_position(self, E2=None):
        """
        Gets the position the channel cut diagnostic needs to move to based on 
        the inputted energy or the current energy of the channel cut line.

        Parameters
        ----------
        E2 : float or None, optional
            Energy in eV to use for the channel cut line. Uses the current 
            energy if None is inputted.

        Returns
        -------
        position : float
            Position in mm the delay diagnostic should move to given the 
            inputted parameters.
        """
        # Use the current theta2 of the system or calc based on inputted energy
        if E2 is None:
            theta2 = self.parent.theta2
        else:
            theta2 = bragg_angle(E=E2)
            
        # Calculate position the diagnostic needs to move to
        position = 2*cosd(theta2)*self.gap
        return position
    
    # @property
    # def aligned(self, rtol=0, atol=0.001):
    #     """
    #     Checks to see if the towers are in aligned in energy and delay.

    #     Parameters
    #     ----------
    #     rtol : float, optional
    #         Relative tolerance to use when comparing value differences.
        
    #     atol : float, optional
    #         Absolute tolerance to use when comparing value differences.

    #     Returns
    #     -------
    #     is_aligned : bool
    #         True if the towers are aligned, False if not.
    #     """
    #     t2 = self.parent.t2
    #     t3 = self.parent.t3
    #     is_aligned = np.isclose(t2.energy, t3.energy, atol=atol, rtol=rtol)
    #     if not is_aligned:
    #         logger.warning("Energy mismatch between t2 and t3. t1: {0:.3f} eV, "
    #                        "t4: {1:.3f} eV".format(t2.energy, t3.energy))
    #     return is_aligned

    def _verify_move(self, E2, string="", use_header=True, confirm_move=True,
                     use_diag=True):
        """
        Prints a summary of the current positions and the proposed positions
        of the motors based on the inputs. It then prompts the user to confirm
        the move.
        
        Parameters
        ----------
        E2 : float
            Desired energy for the channel cut line.

        string : str, optional
            Message to be printed as a prompt.

        use_header : bool, optional
            Adds a basic header to the message.

        confirm_move : bool, optional
            Prompts the user for confirmation.

        use_diag : bool, optional
            Add the diagnostic motor to the list of motors to verify.
        
        Returns
        -------
        allowed : bool
            True if the move is approved, False if the move is not.
        """
        # Add a header to the output
        if use_header:
            string += self._add_verify_header(string)

        # Get move for each motor in the channel cut towers towers
        for tower in self._channelcut_towers:
            for motor, position in zip(tower._energy_motors,
                                       tower._get_move_positions(E2)):
                string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                    motor.desc, motor.position, position)

        # Get move for the channel cut diagnostic
        if use_diag:
            position_dcc = self._get_channelcut_diagnostic_position(E2)
            string += "\n{:<15}|{:^15.4f}|{:^15.4f}".format(
                self.parent.dcc.x.desc, self.parent.dcc.x.position, 
                position_dcc)
            
        # Prompt the user for a confirmation or return the string
        if confirm_move is True:
            return self._confirm_move(string)
        else:
            return string

    def _check_towers_and_diagnostics(self, E2, use_diag=True):
        """
        Checks the staus of the channel cut tower energy motors. Raises the 
        basic motor errors if any of the motors are not ready to be moved.
        
        Parameters
        ----------
        E2 : float
            Desired energy for the channel cut line.

        use_diag : bool, optional
            Check the position of the diagnostic motor.
        
        Raises
        ------
        LimitError
            Error raised when the inputted position is beyond the soft limits.
        
        MotorDisabled
            Error raised if the motor is disabled and move is requested.

        MotorFaulted
            Error raised if the motor is disabled and the move is requested.

        MotorStopped
            Error raised If the motor is stopped and a move is requested.

        BadN2Pressure
            Error raised if the pressure in the tower is bad.

        Returns
        -------
        position_dcc : float or None
            Position to move the channel cut diagnostic to.
        """
        # Check each of the channel cut towers
        for tower in self._channelcut_towers:
            tower.check_status(energy=E2)

        # Check the channel cut diagnostic position
        if use_diag:
            position_dcc = self._get_channelcut_diagnostic_position(E2=E2)
            self.parent.dcc.x.check_status(position_dcc)
            return position_dcc

    def _move_towers_and_diagnostics(self, E2, position_dcc, use_diag=True):
        """
        Moves the channel cut line energy motors and diagnostic to the inputted 
        energy and diagnostic position.
        
        Parameters
        ----------
        E2 : float
            Energy to set the channel cut line to.
        
        position_dcc : float or None, optional
            Position to move the channel cut diagnostic to.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        
        Returns
        -------
        status : list
            Nested list of status objects from each tower.
        """
        status = []            
        # Move the channel cut towers
        status += [tower.set_energy(E2, wait=False, check_status=False) for
                   tower in self._channelcut_towers]
        # Move the channel cut diagnostics
        if use_diag:
            status += [self.parent.dcc.x.move(position_dcc, wait=False)]
        # Log the energy change
        logger.debug("Setting E2 to {0}.".format(E2))

        return status        

    @property
    def position(self):
        """
        Returns the current energy of the channel cut line.
        
        Returns
        -------
        energy : float
            Energy the channel cut line is set to in eV.
        """
        return self.parent.t2.energy

    def set_position(self, E2=None, print_set=True, verify_move=True,
                     use_diag=True):
        """
        Sets the current positions of the motors in the towers to be the 
        calculated positions based on the inputted energies or delay.
        
        Parameters
        ----------
        E2 : float or None, optional
            Energy to set the channel cut line to.
        
        print_set : bool, optional
            Print a message to the console that the set has been made.

        verify_move : bool, optional
            Prints the current system state and a proposed system state and
            then prompts the user to accept the proposal before changing the
            system.

        use_diag : bool, optional
            Move the daignostic motors to align with the beam.
        """
        # Prompt the user about the move before making it
        if verify_move and self._verify_move(E2, use_diag=use_diag):
            return

        # Set position of each E2 motor in each channel cut tower
        for tower in self._channelcut_towers:
            for motor, pos in zip(tower._energy_motors, 
                                  tower._get_move_positions(E2)):
                motor.set_position(pos, print_set=False)

        # Move the cc diagnostic as well
        position_dcc = self._get_channelcut_diagnostic_position(E2)
        self.parent.dcc.x.set_position(position_dcc, print_set=False)

        # Log the set
        if print_set is True:
            logger.info("Setting positions for E2 to {0}.".format(E2))
