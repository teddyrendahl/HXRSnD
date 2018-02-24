"""
Calibration of the delay macromotor
"""
# TODO: Use the uuid implementation in plans.scans
import uuid                               #See plans.scans._short_uid
import logging

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from ophyd.utils import LimitError
from bluesky.plans import scan
from bluesky.plan_stubs import rel_set, wait as plan_wait, abs_set
from bluesky.preprocessors import msg_mutator, stub_wrapper

from pswalker.utils import field_prepend
from pswalker.plans import measure_average, walk_to_pixel

from ..utils import as_list, flatten

logger = logging.getLogger(__name__)

def calibrate_motor(detector, motor, motor_fields, calib_motors, start, 
                    stop, steps, confirm_overwrite=True, *args, **kwargs):
    
    calib_motors = as_list(calib_motors)
    motor_fields = as_list(motor_fields)

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

    # Perform the calibration scan
    df_calib, df_scan = yield from get_calibration_df(
        detector, ['stats2_centroid_x', 'stats2_centroid_y',],
        motor, motor_fields, calib_motors, 
        start, stop, steps, 
        *args, **kwargs)
    
    # load the calibration into the motor
    motor.configure(calib=df_calib, motors=[motor]+calib_motors)
    
def get_calibration_df(detector, detector_fields, motor, motor_fields, 
                       calib_motors, start, stop, steps, first_step=0.01, 
                       average=None, filters=None, tolerance=1, delay=None, 
                       max_steps=5, drop_missing=True, gradients=None, 
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
    if steps <= window_length:
        raise ValueError("Cannot apply savgol filter with window size of {0} "
                         "if number of steps is {1}. Steps must be greater "
                         "than the window size".format(window_length, num))
    # Perform all the initial necessities
    average = average or 1
    calib_motors = as_list(calib_motors)
    system = calib_motors + [motor]
    
    # Lets get the initial positions of the motors
    if return_to_start:
        # Store the current motor position
        initial_motor_positions = {m: m.position for m in [motor]+calib_motors}

    # Perform the calibration scan
    try:
        # TODO: Once rescaling is implemented, split the call here
        df_calibration_scan = yield from calibration_scan(
            detector,
            detector_fields,
            motor,
            motor_fields,
            calib_motors,
            start, stop, steps,
            first_step=first_step,
            average=average,
            filters=filters,
            tolerance=tolerance,
            delay=delay,
            max_steps=max_steps,
            drop_missing=drop_missing,
            gradients=gradients,
            *args, **kwargs)        
        # Get the calibration table for the calib_motors
        df_calibration = process_scan_df(df_calibration_scan, motor, 
                                         motor_fields, calib_motors, 
                                         window_length, polyorder)

    finally:
        # Start returning all the motors to their initial positions
        if return_to_start:
            group = str(uuid.uuid4())
            for mot, pos in initial_motor_positions.items():
                yield from abs_set(mot, pos, group=group)
            # Wait for all the moves to finish if they haven't already
            yield from plan_wait(group=group)

    # Return both the calibration table and the scan info
    return df_calibration, df_calibration_scan

def calibration_scan(detector, detector_fields, motor, motor_fields, 
                     calib_motors, start, stop, steps, first_step=0.01, 
                     average=None, filters=None, tolerance=1, delay=None, 
                     max_steps=5, drop_missing=True, gradients=None, *args, 
                     **kwargs):
    """
    Performs a scan using the motor while holding the initial detector values
    steady using the calib_motors.

    At every step of the scan, the values of the detector fields and the 
    positions of the motor and calibration motors are saved before and after
    the correction. The results are all returned in a pandas DataFrame where the
    indices are the target motor positions. Each detector field will be 
    corrected using the corresponding calibration motor by index. This means the
    calibration scan requires the same number of detector fields as calibration 
    motors.

    Parameters
    ----------
    detector : :class:`.Detector`
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

    Returns
    -------
    df : pd.DataFrame
        DataFrame containing the positions of the detector fields, motor, and
        calibration motors before and after the correction. The indices are the
        target motor positions.
    """
    num = len(detector_fields)
    if len(calib_motors) != num:
        raise ValueError("Must have same number of calibration motors as "
                         "detector fields.")

    # Perform all the initial necessities
    average = average or 1
    calib_motors = as_list(calib_motors)
    first_step = as_list(first_step, num, float)
    tolerance = as_list(tolerance, num)
    gradients = as_list(gradients, num)
    max_steps = as_list(max_steps, num)
    system = calib_motors + [motor]

    # Get the full detector fields
    prep_det_fields = [field_prepend(fld, detector) for fld in detector_fields]
     
    # TODO: Rework centroid scan so it can be used instead of the code below
    
    # Columns of df contains the pre and post correction motors and detectors
    columns = motor_fields + [fld for fld in prep_det_fields] + \
      [m.name + pos for m in calib_motors for pos in ("_pre", "_post")]
                
    # Define the dataframe that will hold all the calibrations
    df = pd.DataFrame(columns=columns, index=np.linspace(start, stop, steps))

    # Define the per_step plan
    def per_step(detectors, motor, step):
        logger.debug("Beginning step '{0}'".format(step))
        # Move the delay motor to the step
        yield from abs_set(motor, step, wait=True)
        # Store the current motor position
        reads = (yield from measure_average(
            detector+system, num=average, filters=filters))
        # Add all the information to the dataframe
        for fld in motor_fields + prep_det_fields:
            df.loc[step, fld] = reads[fld]
        for motor in calib_motors:
            df.loc[step, motor.name+"_pre"] = reads[motor.name]

    # Begin the main plan
    logger.debug("Beginning calibration scan")
    plan = scan([detector], motor, start, stop, steps, per_step=per_step)
    yield from stub_wrapper(plan)
    logger.debug("Completed calibration scan.")
    
    # TODO: Split this off into its own plan

    # Now let's get the detector value to motor position conversion for each fld
    for i, (fld, cmotor) in enumerate(zip(prep_det_fields, calib_motors)):
        # Get a list of devices without the cmotor we are inputting
        inp_system = list(system)
        inp_system.remove(cmotor)

        # Store the current motor and detector value and position
        reads = (yield from measure_average(
            [detector]+system, num=average, filters=filters))
        motor_start = reads[cmotor.name]
        fld_start = reads[fld]
        # Get the farthest detector value we know we can move to
        idx_max = abs(df[fld]-fld_start).values.argmax()
        
        # Walk the cmotor to the first pre-correction detector entry
        logger.debug("Beginning walk to {0} on {1} using {2}".format(
            df.iloc[idx_max][fld], detector.desc, cmotor.desc))
        try:
            yield from walk_to_pixel(detector, 
                                     cmotor, 
                                     df.iloc[idx_max][fld],
                                     filters=filters, 
                                     start=None,
                                     gradient=gradients[i],
                                     models=[],
                                     target_fields=[fld, cmotor.name],
                                     first_step=first_step[i],
                                     tolerance=tolerance[i],
                                     system=inp_system,
                                     average=average,
                                     delay=delay,
                                     max_steps=max_steps[i],
                                     drop_missing=drop_missing)
        except RuntimeError:
            logger.warning("walk_to_pixel raised a RuntimeError for motor '{0}'"
                           ". Using its current position {1} for scale "
                           "calulation.".format(cmotor.desc, cmotor.position))
        except LimitError as exc:
            logger.warning("walk_to_pixel tried to exceed the limits of motor "
                           "'{0}'. Using current position '{1}' for scale "
                           "calculation.".format(cmotor.desc, cmotor.position))
        
        # Get the positions and values we moved to
        reads = (yield from measure_average(
            [detector]+system, num=average, filters=filters))
        motor_end = reads[cmotor.name]
        fld_end = reads[fld]

        # Now lets find the conversion from signal value to motor distance
        distance_per_value = (motor_end-motor_start) / (fld_end-fld_start)
        # Use the conversion to create an expected correction table
        df[cmotor.name+"_post"] = motor_start - \
          (df[fld] - df[fld].iloc[0]) * distance_per_value

    return df

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
