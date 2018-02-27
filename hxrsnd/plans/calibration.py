"""
Calibration of the delay macromotor
"""
import logging

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from ophyd.utils import LimitError
from bluesky.plans import scan
from bluesky.utils import short_uid
from bluesky.plan_stubs import rel_set, wait as plan_wait, abs_set, checkpoint
from bluesky.preprocessors import msg_mutator, stub_wrapper

from pswalker.utils import field_prepend
from pswalker.plans import measure_average, walk_to_pixel

from .scans import centroid_scan
from ..utils import as_list, flatten

logger = logging.getLogger(__name__)

def calibrate_motor(detector, motor, motor_fields, calib_motors, start, 
                    stop, steps, confirm_overwrite=True, *args, **kwargs):
    
    calib_motors = as_list(calib_motors)
    motor_fields = as_list(motor_fields or motor.read_attrs)

    # Check for motor having a _calib field
    motor_config = motor.read_configuration()
    if motor_config['calib']['value'] and motor_config['motors']['value']:
        logger.warning("Running the calibration procedure will overwrite the "
                       "existing calibration.")        
        # If a calibration is loaded, prompt the user for verification
        if confirm_overwrite:
            # Prompt the user about the move before making it
            try:
                response = input("\nConfirm Overwrite [y/n]: ")
            except Exception as e:
                logger.warning("Exception raised: {0}".format(e))
                response = "n"
            if response.lower() != "y":
                logger.info("\Calibration cancelled.")
                return
            logger.debug("\nOverwrite confirmed.")

    # Lets get the initial positions of the motors
    if return_to_start:
        # Store the current motor positions
        initial_motor_positions = {m : m.position for m in [motor]+calib_motors}
        
    try:
        # Perform the calibration scan
        df_calib, df_scan, scaling, start_pos = yield from calibration_scan(
            detector, ['stats2_centroid_x', 'stats2_centroid_y',],
            motor, motor_fields,
            calib_motors, 
            start, stop, steps, 
            *args, **kwargs)

    finally:
        # Start returning all the motors to their initial positions
        if return_to_start:
            group = short_uid('set')
            for mot, pos in initial_motor_positions.items():
                yield from abs_set(mot, pos, group=group)
            # Wait for all the moves to finish if they haven't already
            yield from plan_wait(group=group)
    
    # load the calibration into the motor
    motor.configure(calib=df_calib, motors=[motor]+calib_motors, scale=scaling,
                    start=start_pos)
    
def calibration_scan(detector, detector_fields, motor, motor_fields, 
                     calib_motors, calib_fields, start, stop, steps,
                     first_step=0.01, average=None, filters=None, tolerance=1,
                     delay=None, max_steps=5, drop_missing=True, gradients=None, 
                     return_to_start=True, window_length=9, polyorder=3, 
                     mode='absolute', *args, **kwargs):
    """
    Performs a calibration scan for the main motor and returns a correction
    table for the calibration motors.

    This adds to ``calibration_scan`` by moving the motors to their original
    positions and and running the calibration calculation function. It returns
    the expected motor calibration given the results from the scan, as well as
    the dataframe from the scan with all the data.

    Parameters
    ----------
    detector : :class:`.BeamDetector`
        Detector from which to take the value measurements

    detector_fields : iterable
        Fields of the detector to measure

    motor : :class:`.Motor`
        Main motor to perform the scan

    calib_motors : iterable, :class:`.Motor`
        Motor to calibrate each detector field with

    start : float
        Starting position of motor

    stop : float
        Ending position of motor

    steps : int
        Number of steps to take
    
    first_step : float, optional
        First step to take on each calibration motor when performing the 
        correction

    average : int, optional
        Number of averages to take for each measurement

    delay : float, optional
        Time to wait inbetween reads    

    tolerance : float, optional
        Tolerance to use when applying the correction to detector field

    max_steps : int, optional
        Limit the number of steps the correction will take before exiting
    
    gradients : float, optional
        Assume an initial gradient for the relationship between detector value
        and calibration motor position

    return_to_start : bool, optional
        Move all the motors to their original positions after the scan has been
        completed
    
    window_length : int, optional
        The length of the filter window (i.e. the number of coefficients). 
        window_length must be a positive odd integer.

    polyorder : int. optional
        The order of the polynomial used to fit the samples. polyorder must be 
        less than window_length.

    mode : str, optional
        The mode for computing the calibration table

    Returns
    -------
    df_calibration : pd.DataFrame
        Dataframe containing the points to be used for the calibration by the
        macromotor.

    df_calibration_scan : pd.DataFrame
        DataFrame containing the positions of the detector fields, motor, and
        calibration motors before and after the correction. The indices are the
        target motor positions.
    """
    num = len(detector_fields)
    calib_fields = as_list(calib_fields or [m.name for m in calib_motors])
    if steps <= window_length:
        raise ValueError("Cannot apply savgol filter with window size of {0} "
                         "if number of steps is {1}. Steps must be greater "
                         "than the window size".format(window_length, num))    
    if len(calib_motors) != num:
        raise ValueError("Must have same number of calibration motors as "
                         "detector fields.")
    if len(calib_fields) != num:
        raise ValueError("Must have same number of calibration fields as "
                         "detector fields.")
    
    # Perform the main scan, reading the positions of all the devices
    logger.debug("Beginning calibration scan")
    df_scan = yield from calibration_centroid_scan(
        detector, motor, calib_motors,
        start, stop, steps,
        detector_fields=detector_fields,
        motor_fields=motor_fields,
        calib_fields=calib_fields,
        average=average,
        filters=filters)

    # Find the distance per detector value scaling and initial positions used
    scaling, start_positions = yield from detector_scaling_walk(
        df_scan,
        detector,
        motor,
        calib_motors,
        first_step=first_step,
        average=average,
        filters=filters,
        tolerance=tolerance,
        max_steps=max_steps,
        drop_missing=drop_missing,
        gradients=gradients,
        *args, **kwargs)

    # Rescale the scan df
    df_scan_scaled = scale_scan_df(df_scan, scaling, start_positions, detector,
                                   calib_fields)

    # Process the scan df into the final calibration table for the calib_motors
    df_calibration = process_scan_df(df_scan_scaled, motor, motor_fields,
                                     calib_motors, calib_fields, window_length,
                                     polyorder)
    
    # Return both the calibration table and the scan info
    logger.debug("Completed calibration scan.")
    return df_calibration, df_scan_scaled, scaling, start_positions

def calibration_centroid_scan(detector, motor, calib_motors, start, stop, steps,
                              calib_fields=None, *args, **kwargs):
    """
    Performs a centroid scan producing a dataframe with the values of the
    detector, motor, and calibration motor fields.
    Parameters
    ----------
    detector : :class:`.BeamDetector`
        Detector from which to take the value measurements
    
    motor : :class:`.Motor`
        Main motor to perform the scan

    calib_motors : iterable
        Calibration motors

    start : float
        Starting position of motor

    stop : float
        Ending position of motor

    steps : int
        Number of steps to take
    
    average : int, optional
        Number of averages to take for each measurement

    detector_fields : iterable, optional
        Fields of the detector to add to the returned dataframe

    motor_fields : iterable, optional
        Fields of the motor to add to the returned dataframe
    
    calib_fields : list, optional
        Fields of the of the calibration motors to add to the returned dataframe

    Returns
    -------
    df : pd.DataFrame
        DataFrame containing the detector, motor, and calibration motor fields
        at every step of the scan.
    """
    calib_fields = as_list(calib_fields or [m.name for m in calib_motors])

    # Make sure the same number of calibration fields as motors are passed
    if len(calib_motors) != len(calib_fields):
        raise ValueError("Must one calibration field for every calibration "
                         "motor, but got {0} fields for {1} motors.".format(
                             len(calib_fields), len(calib_motors)))

    # Perform the main scan, correctly passing the calibration parameters 
    df = yield from centroid_scan(detector, motor,
                                  start, stop, steps,
                                  system=calib_motors,
                                  system_fields=calib_fields,
                                  return_to_start=False
                                  *args, **kwargs)

    # Let's adjust the column names of the calib motors
    df.columns = [c+"_pre" if c in calib_fields else c for c in df.columns]
    return df    

def detector_scaling_walk(df_scan, detector, motor, calib_motors,
                          first_step=0.01, average=None, filters=None,
                          tolerance=1, delay=None, max_steps=5,
                          drop_missing=True, gradients=None, *args, **kwargs):
    """Performs a walk to to the detector value farthest from the current value
    using each of calibration motors, and then determines the motor to detector
    scaling

    Using the inputted scan dataframe, the plan loops through each detector
    field, then finds the value that is farthest from the current value, and
    then performs a walk_to_pixel to that value using the corresponding
    calibration motor. Since the final absolute position does not matter so long
    as it is recorded, if a RuntimeError or LimitError is raised, the plan will
    simply use the current motor position for the scaling calculation.

    Parameters
    ----------
    df_scan : pd.DataFrame
        Dataframe containing the results of a centroid scan performed using the
        detector, motor, and calibration motors.
    
    detector : :class:`.Detector`
        Detector from which to take the value measurements

    motor : :class:`.Motor`
        Main motor to perform the scan

    calib_motors : iterable, :class:`.Motor`
        Motor to calibrate each detector field with
   
    first_step : float, optional
        First step to take on each calibration motor when performing the 
        correction

    average : int, optional
        Number of averages to take for each measurement

    delay : float, optional
        Time to wait inbetween reads    

    tolerance : float, optional
        Tolerance to use when applying the correction to detector field

    max_steps : int, optional
        Limit the number of steps the correction will take before exiting
    
    drop_missing : bool, optional
        Choice to include events where event keys are missing

    gradients : float, optional
        Assume an initial gradient for the relationship between detector value
        and calibration motor position

    Returns
    -------
    scaling : list
        List of scales in the units of motor egu / detector value

    start_positions : list
        List of the initial positions of the motors before the walk
    """
    detector_fields = [col for col in df_scan.columns if detector.name in col]
    num = len(detector_fields)
    
    # Perform all the initial necessities
    average = average or 1
    calib_motors = as_list(calib_motors)
    first_step = as_list(first_step, num, float)
    tolerance = as_list(tolerance, num)
    gradients = as_list(gradients, num)
    max_steps = as_list(max_steps, num)
    system = calib_motors + [motor]
    
    # Define the list that will hold the scaling
    scaling, start_positions = [], []

    # Now let's get the detector value to motor position conversion for each fld
    for i, (fld, cmotor) in enumerate(zip(detector_fields, calib_motors)):
        # Get a list of devices without the cmotor we are inputting
        inp_system = list(system)
        inp_system.remove(cmotor)

        # Store the current motor and detector value and position
        reads = yield from measure_average([detector]+system,
                                            num=average,
                                            filters=filters)
        motor_start = reads[cmotor.name]
        fld_start = reads[fld]
        
        # Get the farthest detector value we know we can move to from the
        # current position
        idx_max = abs(df_scan[fld] - fld_start).values.argmax()
        
        # Walk the cmotor to the first pre-correction detector entry
        try:
            logger.debug("Beginning walk to {0} on {1} using {2}".format(
                df_scan.iloc[idx_max][fld], detector.name, cmotor.name))
            yield from walk_to_pixel(detector, 
                                     cmotor, 
                                     df_scan.iloc[idx_max][fld],
                                     filters=filters, 
                                     gradient=gradients[i],
                                     target_fields=[fld, cmotor.name],
                                     first_step=first_step[i],
                                     tolerance=tolerance[i],
                                     system=inp_system,
                                     average=average,
                                     max_steps=max_steps[i]
                                     *args, **kwargs)
            
        except RuntimeError:
            logger.warning("walk_to_pixel raised a RuntimeError for motor '{0}'"
                           ". Using its current position {1} for scale "
                           "calulation.".format(cmotor.desc, cmotor.position))
        except LimitError:
            logger.warning("walk_to_pixel tried to exceed the limits of motor "
                           "'{0}'. Using current position '{1}' for scale "
                           "calculation.".format(cmotor.desc, cmotor.position))
        
        # Get the positions and values we moved to
        reads = (yield from measure_average([detector]+system,
                                            num=average,
                                            filters=filters))
        motor_end = reads[cmotor.name]        
        fld_end = reads[fld]

        # Now lets find the conversion from signal value to motor distance
        scaling.append((motor_end - motor_start)/(fld_end - fld_start))
        # Add the starting position to the motor start list
        start_positions.append(motor_start)

    # Return the final scaling list
    return scaling, start_positions

def scale_scan_df(df_scan, scaling, start_positions, detector, calib_fields):
    """
    Takes the scaling and starting positions of the detector values and uses it
    to rescale the calibration motor positions.
    """
    # Get the detector fields being used in the scan df
    detector_fields = [col for col in df_scan.columns if detector.name in col]
    if len(detector_fields) != len(calib_fields):
        raise ValueError("Must have same number of calibration fields as "
                         "detector fields, but got {0} and {1}.".format(
                             len(calib_fields), len(detector_fields)))
    
    # Use the conversion to create an expected correction table
    for scale, start, cfld, dfld in zip(scaling, start_positions, calib_fields,
                                        detector_fields):
        df_scan[cfld+"_post"] = start - (df_scan[dfld]-df_scan[dfld].iloc[0]) \
                               * scale

    return df_scan

def process_scan_df(df_calibration_scan, motor, motor_fields, calib_motors, 
                    window_length=9, polyorder=3, mode="absolute"):
    """
    Takes the dataframe returned by ``calibration_scan`` and returns a 
    calibration table.

    The initial table is created depending on the inputted mode. For 'absolute'
    the table is simply the positions of the calibration motors after the
    correction has been added. For 'relative' the table is the difference 
    between the motor positions after and before the correction.

    After this table has been created, a Savitzky-Golay filter is applied to 
    each of the columns using the inputted window length and polynomial order.

    The columns names are the names of the motor with underscores replaced with
    dots, that way they can be accessed using ``getattr`` on the parent device.

    Parameters
    ----------
    df_calibration_scan : pd.DataFrame
        DataFrame containing the positions of the detector fields, motor, and
        calibration motors before and after the correction

    motor : :class:`.Motor`
        Main motor that was used to perform the calibration scan.

    calib_motors : iterable, :class:`.Motor`
        Motors that were used to perform the calibration.

    window_length : int, optional
        The length of the filter window (i.e. the number of coefficients). 
        window_length must be a positive odd integer.

    polyorder : int. optional
        The order of the polynomial used to fit the samples. polyorder must be 
        less than window_length.

    mode : str, optional
        The mode for computing the calibration table

    Returns
    -------
    df_calibration : pd.DataFrame
        Dataframe containing the points to be used for the calibration by the
        macromotor.

    Raises
    ------
    ValueError
        If an invalid mode is inputted
    """
    # Dictionary of just the final positions for each calib motor
    if mode == "absolute":
        calibration_dict = {cmotor.desc : 
                            df_calibration_scan[cmotor.name+"_post"]
                            for cmotor in calib_motors}

    # Dictionary of the differnce between the start and end positions
    elif mode == "relative":
        calibration_dict = {cmotor.desc : 
                            (df_calibration_scan[cmotor.name+"_post"] -
                             df_calibration_scan[cmotor.name+"_pre"])
                            for cmotor in calib_motors}
    else:
        raise ValueError("Mode can only be 'absolute' or 'relative'.")

    # TODO: Make the filter optional
    
    # Filter the corrections 
    df_filtered = pd.DataFrame(calibration_dict).apply(
        savgol_filter, args=(window_length, polyorder))

    # Add the scan motor positions
    df_calibration = pd.concat([df_calibration_scan[motor_fields[0]], 
                                df_filtered], axis=1)
    
    return df_calibration
