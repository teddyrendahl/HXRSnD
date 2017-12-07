"""
Hold all of the Bluesky plans for HXRSnD operations
"""
############
# Standard #
############
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
    
    gradient : float, optional
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
