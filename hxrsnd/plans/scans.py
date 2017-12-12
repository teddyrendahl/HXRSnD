"""
Scans for HXRSnD
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import numpy as np
import pandas as pd
from bluesky                    import Msg
from bluesky.plans              import scan
from bluesky.utils              import short_uid as _short_uid
from bluesky.plan_stubs         import checkpoint, trigger_and_read
from bluesky.plan_stubs         import abs_set
from bluesky.preprocessors      import stage_decorator, run_decorator
from bluesky.preprocessors      import msg_mutator

########
# SLAC #
########
from pswalker.utils             import field_prepend
from pswalker.plans             import measure_average

##########
# Module #
##########
from .plan_stubs import block_run_control

logger = logging.getLogger(__name__)

def linear_scan(motor, start, stop, num, use_diag=True, return_to_start=True, 
                md=None, *args, **kwargs):
    """
    Linear scan of a motor without a detector.
    
    Performs a linear scan using the inputted motor, optionally using the
    diagnostics, and optionally moving the motor back to the original start
    position. This scan is different from the regular scan because it does not
    take a detector, and simply scans the motor.

    Parameters
    ----------
    motor : object
        any 'setable' object (motor, temp controller, etc.)

    start : float
        starting position of motor

    stop : float
        ending position of motor

    num : int
        number of steps
        
    use_diag : bool, optional
        Include the diagnostic motors in the scan.

    md : dict, optional
        metadata
    """
    # Save some metadata on this scan
    _md = {'motors': [motor.name],
           'num_points': num,
           'num_intervals': num - 1,
           'plan_args': {'num': num,
                         'motor': repr(motor),
                         'start': start, 
                         'stop': stop},
           'plan_name': 'daq_scan',
           'plan_pattern': 'linspace',
           'plan_pattern_module': 'numpy',
           'plan_pattern_args': dict(start=start, stop=stop, num=num),
           'hints': {},
          }
    _md.update(md or {})

    # Build the list of steps
    steps = np.linspace(**_md['plan_pattern_args'])
    
    # Let's store this for now
    start = motor.position
    
    # Define the inner scan
    @stage_decorator([motor])
    @run_decorator(md=_md)
    def inner_scan():
        
        for i, step in enumerate(steps):
            logger.info("\nStep {0}: Moving to {1}".format(i+1, step))
            grp = _short_uid('set')
            yield Msg('checkpoint')
            # Set wait to be false in set once the status object is implemented
            yield Msg('set', motor, step, group=grp, *args, **kwargs)
            yield Msg('wait', None, group=grp)
            yield from trigger_and_read([motor])

        if return_to_start:
            logger.info("\nScan complete. Moving back to starting position: {0}"
                        "\n".format(start))
            yield Msg('set', motor, start, group=grp, use_diag=use_diag, *args,
                      **kwargs)
            yield Msg('wait', None, group=grp)

    return (yield from inner_scan())    

def centroid_scan(detector, motor, start, stop, steps, average=None, 
                  detector_fields=['centroid_x', 'centroid_y',], filters=None,
                  *args, **kwargs):
    """
    Performs a scan and returns the centroids of the inputted detector.

    The returned centroids can be absolute or relative to the initial value. The
    values are returned in a pandas DataFrame where the indices are the target
    motor positions.

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
        DataFrame containing the centroids of the detector, 
    """
    average = average or 1
    # Get the full detector fields
    prep_det_fields = [field_prepend(fld, detector) for fld in detector_fields]

    # Build the dataframe with the centroids
    df = pd.DataFrame(index=range(start, stop, steps), columns= 
                      prep_det_fields + [motor.name])

    # Create a basic measuring plan
    def measure(detectors, motor, step):
        # Perform step
        logger.debug("Measuring average at step {0} ...".format(step))
        yield from checkpoint()
        yield from abs_set(motor, step, wait=True)
        # Measure the average
        reads = (yield from measure_average([motor, detector], num=average,
                                            filters=filters))
        # Fill the dataframe at this step with the centroid difference
        df.loc[step, motor.name] = reads[motor.name]
        for fld in prep_det_fields:
            df.loc[step, fld] = reads[fld]
                
    # Define the generic scans and run it
    plan = scan([detector], motor, start, stop, steps, per_step=measure)
    yield from msg_mutator(plan, block_run_control)

    # Return the filled dataframe
    return df
    
