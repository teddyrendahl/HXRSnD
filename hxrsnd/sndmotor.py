"""
Script for abstract motor classes used in the SnD.
"""
import time
import logging
from functools import reduce
from collections import OrderedDict

import pandas as pd
from ophyd.device import Component as Cmp
from ophyd.signal import Signal
from ophyd.utils import LimitError
from pcdsdevices.epics_motor import PCDSMotorBase
from pcdsdevices.mv_interface import FltMvInterface
from bluesky.preprocessors  import run_wrapper
from pcdsdevices.signal import Signal

from .snddevice import SndDevice
from .plans.calibration import calibrate_motor
from .plans.preprocessors import return_to_start as _return_to_start
from .exceptions import InputError
from .utils import as_list

logger = logging.getLogger(__name__)


class SndMotor(FltMvInterface, SndDevice):
    """
    Base Sndmotor class that has methods common to all the various motors,
    even
    the non-EpicsMotor ones.
    """
    pass


class SndEpicsMotor(PCDSMotorBase, SndMotor):
    """
    SnD motor that inherits from EpicsMotor, therefore having all the relevant 
    signals
    """
    direction_of_travel = Cmp(Signal)


class SamMotor(SndMotor):
    offset_freeze_switch = Cmp(Signal)
    home_forward = Cmp(Signal)
    home_reverse = Cmp(Signal)

    def check_value(self, value, retries=5):
        """
        Check if the value is within the soft limits of the motor.

        Raises
        ------
        ValueError
        """
        if value is None:
            raise ValueError('Cannot write None to epics PVs')
            
        for i in range(retries):
            try:
                low_limit, high_limit = self.limits
                if not (low_limit <= value <= high_limit):
                    raise LimitError("Value {} outside of range: [{}, {}]"
                                     .format(value, low_limit, high_limit))
                return
            except TypeError:
                logger.warning("Failed to get limits, retrying...")
                if i == retries-1:
                    raise


# TODO: Add a centroid scanning method
# TODO: Add ability to save caibrations to disk
# TODO: Add ability to load calibrations from disk
# TODO: Add ability to display calibrations
# TODO: Add ability to change post-processing done to scan. 
# TODO: Add ability to redo scaling on scan
class CalibMotor(SndDevice):
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
        self._calib = OrderedDict()
        self.configure()

    def calibrate(self, start, stop, steps, average=100, confirm_overwrite=True,
                  detector=None, detector_fields=None, RE=None,
                  return_to_start=True, *args, **kwargs):
        """Performs a calibration scan for this motor and updates the 
        configuration.

        Warning: This has not been commissioned.

        Parameters
        ----------
        start : float
            Starting position of motor

        stop : float
            Ending position of motor

        steps : int
            Number of steps to take

        average : int, optional
            Number of averages to take for each measurement

        confirm_overwrite : bool, optional
            Prompt the user if this plan will overwrite an existing calibration

        detector : :class:`.BeamDetector`, optional
            Detector from which to take the value measurements

        detector_fields : iterable, optional
            Fields of the detector to measure

        RE : RunEngine, optional
            Bluesky runengine instance to run the calibration plan.

        return_to_start : bool, optional
            Move all the motors to their original positions after the scan has been
            completed        
        """
        # Remove this once the calibration routine has been tested
        logger.warning('Calibration functionality has not been commissioned.')

        # Use the inputted runengine or the parent's
        RE = RE or self.parent.RE
        detector = detector or self.calib_detector
        detector_fields = detector_fields or self.detector_fields

        # Make sure everything returns to the starting position when finished
        @_return_to_start(self, *self.calib_motors, perform=return_to_start)
        def inner():
            _, _ = yield from calibrate_motor(
                detector,
                detector_fields,
                self, 
                self.motor_fields,
                self.calib_motors,
                self.calib_fields,
                start, stop, steps,
                average=average,
                confirm_overwrite=confirm_overwrite,
                return_to_start=False,
                *args, **kwargs)
            
        # Run the inner plan
        RE(run_wrapper(inner()))

    @property
    def calibration(self):
        """
        Returns the current calibration of the motor as a dictionary.
        
        Returns
        -------
        calibration : dict
            Dictionary containing calib, motors, scan, scale, and start 
            calibration parameters.
        """
        if self.has_calib:
            config = self.read_configuration()
            # Grab the values of each of the calibration parameters
            calib = {fld : config[fld]['value'] 
                     for fld in ['calib', 'scan', 'scale', 'start']}
            # Make sure there are motors before we iterate through the list
            if config['motors']['value']:
                # If the motors have name attributes, just return those
                calib['motors'] = [mot.name if hasattr(mot, 'name') else mot 
                                   for mot in config['motors']['value']]
            else:
                calib['motors'] = None
            return calib
        else: 
            return None

    def configure(self, *, calib=None, motors=None, scan=None, scale=None, 
                  start=None):
        """
        Configure the calib-motor's move parameters.

        Parameters
        ----------
        calib : DataFrame, optional
            Lookup table for move calibration. This represents set positions of
            auxiliary movers that should be chosen as we move our main macro.

        motors : list, optional
            List of calibration motors

        scan : pd.DataFrame, optional
            Dataframe of the centroid scan used to compute the correction table

        scale : list, optional
            List of scales in the units of motor egu / detector value

        start : list, optional
            List of the initial positions of the motors before the walk        
        
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
        Handle the calibration arguments, and update the config dictionary
        accordingly.

        Parameters
        ----------
        calib : DataFrame
            Lookup table for move calibration. This represents set positions of
            auxiliary movers that should be chosen as we move our main macro.

        motors : list
            List of calibration motors

        scan : pd.DataFrame
            Dataframe of the centroid scan used to compute the correction table

        scale : list
            List of scales in the units of motor egu / detector value

        start : list
            List of the initial positions of the motors before the walk        
        """
        # Start with all the previous calibration parameters
        save_calib = OrderedDict(self._calib)
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
        """
        Internal method that checks the values passed in the calibration dict
        to make sure they are valid before actually saving it. It will raise
        errors or send warnings depending on the inputs.

        Raises
        ------
        InputError
            If a correction table is passed without motors or the correction
            table and motors have a mismatched number of columns and motors.

        TypeError
            If a correction table is passed that is not a dataframe.        
        """
        # Let's get all the values we will update the calibration with
        calib = save_calib['calib']['value']
        motors = save_calib['motors']['value']
        scan = save_calib['scan']['value']
        scale = save_calib['scale']['value']
        start = save_calib['start']['value']

        # If no correction table is passed, then there isn't anything to check
        if calib is None: pass

        # We have a correction table but it isnt a Dataframe
        elif not isinstance(calib, pd.DataFrame):
            raise TypeError("Only Dataframes are supported for calibrations "
                            "tables at this time. Got a calibration of type "
                            "{0}.".format(type(calib)))

        # We have a correction table but no motors to correct with
        elif not motors:
            raise InputError("Inputted a correction table with no calibration "
                             "motors.")

        # We have a correction table and calibration motors, but they arent the
        # same length, so we cannot actually use it
        elif len(calib.columns) != len(motors):
            raise InputError("Mismatched calibration size and number of "
                             "motors. Got {0} columns for {1} motors.".format(
                                len(calib.columns),len(motors)))

        # We have the correct correction table and motors but one of the of the
        # extra parameters were not passed, which is critical for corrected
        # motions but warn the user
        elif scan is None or not scale or not start:
            logger.warning("Inputted correction table and calibration motors "
                           "but not all configuration data. Some calibration "
                           "updating methods may not be functional!")

    def _calib_compensate(self, position, *args, **kwargs):
        """
        Perform the additional corrected motions if there is a valid calibration
        and the user has indicated that they want to perform them.

        Parameters
        ---------- 
        position
            Position to move to.

        Returns
        -------
        status : AndStatus
            Status objects of all the extra motions performed.
        """
        # Grab the current calibration
        calib = self._calib['calib']['value']
        motors = self._calib['motors']['value']
        status_list = []

        # Only perform the compensation if there is a valid calibration and we
        # want to use the calibration
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
        interpolated_row = slopes * (position-first[0]) + first

        # Move each calibration motor to the interpolated position
        for i, motor in enumerate(motors[1:]):
            status = motor.move(interpolated_row[i+1], *args, **kwargs)
            status_list.append(status)

        # Reduce all the status objects into one AndStatus object and return it
        return reduce(lambda x, y: x & y, status_list)

    @property
    def has_calib(self):
        """
        Indicator if there is a valid calibration that can be used to perform
        correction moves.
        
        Because the only requirements to perform a corrected move are the
        correction table and the calibration motors, they are the only
        calibration parameters that must be defines. These parameters must also
        pass ``_check_calib`` without raising any exceptions.
        
        Returns
        -------
        has_calib : bool
            True if there is a calibration that can be used for correction 
            motion, False otherwise.
        """
        # Grab the current correction table and calibration motors
        calib = self._calib['calib']['value']
        motors = self._calib['motors']['value']

        # Return False if we dont have a correction table
        if calib is None:
            return False
        try:
            # If we make it through the check, we have a valid calibration
            self._check_calib(self._calib)
            return True
        except:
            # An exception was raised, the config is somehow invalid
            return False

    @property
    def use_calib(self):
        """
        Returns whether the user indicated that corrected motions should be 
        used.
        
        Returns
        -------
        use_calib : bool
            Internal indicator if the user wants to perform correction motions.
        """
        return self._use_calib
    
    @use_calib.setter
    def use_calib(self, indicator):
        """
        Setter for use_calib. Will warn the user if corrected motions are 
        desired but there is no valid configuration to use.
        
        Parameters
        ----------
        indicator : bool
            Indicator for whether corrected motions should be performed or not.
        """
        self._use_calib = bool(indicator)
        if self._use_calib is True and not self.has_calib:
            logger.warning("use_calib is currently set to True but there is "
                           "no valid calibration to use")
    
    def read_configuration(self):
        return self._calib

    def describe_configuration(self):
        if not self._calib:
            return super().describe_configuration()
        if isinstance(self._calib['calib']['value'], pd.DataFrame):
            shape = self._calib['calib']['value'].shape
        else:
            shape = [len(self._calib)]
        return OrderedDict(**dict(calib=dict(source='calibrate', dtype='array', 
                                  shape=shape)), 
                           **super().describe_configuration())

