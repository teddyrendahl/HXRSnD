"""
Calibration of the delay macromotor
"""
############
# Standard #
############
import uuid
import logging

###############
# Third Party #
###############
import pandas as pd
from scipy.signal               import savgol_filter
from bluesky.plans              import scan
from bluesky.plan_stubs         import rel_set, wait as plan_wait
from bluesky.plan_stubs         import abs_set
from bluesky.preprocessors      import msg_mutator

##########
# Module #
##########
from pswalker.utils             import field_prepend
from pswalker.plans             import measure_average, walk_to_pixel

##########
# Module #
##########
from .plan_stubs import block_run_control
from ..utils import as_list

logger = logging.getLogger(__name__)

def motor_calibration(detector, detector_fields, motor, calib_motors, start, 
                      stop, steps, first_step=0.1, average=None, filters=None, 
                      tolerance=.01, delay=None, diag_motor=None, 
                      diag_motor_position=-12.5, max_steps=None, 
                      drop_missing=True, gradients=None, return_to_start=True, 
                      window_length=9, polyorder=3, mode='absolute', *args, 
                      **kwargs):
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
    # Perform all the initial necessities
    average = average or 1
    calib_motors = as_list(calib_motors)
    system = calib_motors + [motor]
    
    # Move the diagnostic motor out of the way
    if diag_motor is not None:
        diag_motor_start_position = diag_motor.read()[diag_motor.name]['value']
        yield from rel_set(diag_motor, diag_motor_position, wait=True)

    # Lets get the initial positions of the motors
    if return_to_start:
        # Store the current motor position
        reads = (yield from measure_average([detector]+system, num=average, 
                                            filters=filters))
        initial_motor_positions = {mot:reads[mot.name] for mot in system}

    # Perform the calibration scan
    df_calibration_scan = yield from calibration_scan(detector,
                                                      detector_fields,
                                                      motor,
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

    # Start returning all the motors to their initial positions
    if return_to_start:
        group = str(uuid.uuid4())
        for mot, pos in initial_motor_positions.items():
            yield from abs_set(mot, pos, group=group)
        if diag_motor is not None:
            yield from abs_set(diag_motor, diag_motor_position, group=group)
            
    # Get the calibration table for the calib_motors
    df_calibration = get_df_calibration(df_calibration_scan, calib_motors,
                                        window_length, polyorder)
    
    # Wait for all the moves to finish if they haven't already
    if return_to_start:
        yield from plan_wait(group=group)

    return df_calibration, df_calibration_scan

def calibration_scan(detector, detector_fields, motor, calib_motors, start, 
                     stop, steps, first_step=0.1, average=None, filters=None,
                     tolerance=.01, delay=None, max_steps=None, 
                     drop_missing=True, gradients=None, *args, **kwargs):
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
 
    # Columns of df contains the pre and post correction motors and detectors
    columns = \
      [m.name + pos for m in calib_motors for pos in ("_pre", "_post")] + \
      [fld + pos for fld in prep_det_fields for pos in ("_pre", "_post")] + \
      [motor.name + pos for pos in ["_pre", "_post"]]
                
    # Define the dataframe that will hold all the calibrations
    df = pd.DataFrame(index=range(start, stop, steps), columns=columns)

    # Define the per_step plan
    def per_step(detector, motor, step):
        logger.debug("Beginning step '{0}'".format(step))
        # Move the delay motor to the step
        yield from abs_set(motor, step, wait=True)

        # Store the current motor position
        reads = (yield from measure_average(detector+system, num=average, 
                                            filters=filters))
        df.loc[step, motor.name+"_pre"] = reads[motor.name]
        for fld in prep_det_fields:
            df.loc[step, fld+"_pre"] = reads[fld]
        for cmotor in calib_motors:
            df.loc[step, cmotor.name+"_pre"] = reads[cmotor.name]
        
        for i, (fld, cmotor) in enumerate(zip(prep_det_fields, calib_motors)):
            # Get a list of devices without the cmotor we are inputting
            inp_system = list(system)
            inp_system.remove(cmotor)
            # Walk the cmotor to the first pre-correction detector entry
            yield from walk_to_pixel(detector[0], 
                                     cmotor, 
                                     df.iloc[0][fld+"_pre"],
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
            
        # Add the post-correction detector values and motor positions
        reads = (yield from measure_average(detector+system, num=average, 
                                            filters=filters))
        df.loc[step, motor.name+"_post"] = reads[motor.name]
        for fld in prep_det_fields:
            df.loc[step, fld+"_post"] = reads[fld]
        for cmotor in calib_motors:
            df.loc[step, cmotor.name+"_post"] = reads[cmotor.name]

    # Begin the plan
    logger.debug("Beginning calibration scan")
    # Begin the main scan and then return the dataframe
    plan = scan([detector], motor, start, stop, steps, per_step=per_step)
    yield from msg_mutator(plan, block_run_control)
    return df

def get_df_calibration(df_calibration_scan, calib_motors, window_length=9, 
                       polyorder=3, mode="absolute"):
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

    calib_motors : iterable, :class:`.Motor`
        Motor to calibrate each detector field with

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
        calibration_dict = {m.name[1].replace("_",".") :
            df_calibration_scan[m.name+"_post"] for m in calib_motors}

    # Dictionary of the differnce between the start and end positions
    elif mode == "relative":
        calibration_dict = {m.name[1].replace("_",".") :
                            df_calibration_scan[m.name+"_post"] - 
                            df_calibration_scan[m.name+"_pre"]
                            for m in calib_motors}
    else:
        raise ValueError("Mode can only be 'absolute' or 'relative'.")
    # Get the calibration 
    df_calibration= pd.DataFrame(
        calibration_dict, index=df_calibration_scan.index).apply(
            savgol_filter, args=(window_length, polyorder))

    return df_calibration
