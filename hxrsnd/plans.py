"""
Hold all of the Bluesky plans for HXRSnD operations
"""
############
# Standard #
############
import time
import logging
import math 

###############
# Third Party #
###############
import numpy as np
import pandas as pd
from lmfit.models               import LorentzianModel
from bluesky                    import Msg
from bluesky.preprocessors      import msg_mutator, subs_decorator
from bluesky.preprocessors      import stage_decorator, run_decorator
from bluesky.plan_stubs         import abs_set, checkpoint, trigger_and_read
from bluesky.plan_stubs         import rel_set
from bluesky.plans              import scan, list_scan
from bluesky.utils              import short_uid as _short_uid

##########
# Module #
##########
from pswalker.callbacks         import LiveBuild
from pswalker.plans             import measure_average, walk_to_pixel
from pswalker.utils             import field_prepend

##########
# Module #
##########
from .utils import as_list
from .errors import UndefinedBounds

logger = logging.getLogger(__name__)

# Used to strip `run_wrapper` off of plan
# Should probably be added as bluesky PR
def block_run_control(msg):
    """
    Block open and close run messages
    """
    if msg.command in ['open_run', 'close_run']:
        return None

    return msg

def maximize_lorentz(detector, motor, read_field, step_size=1,
                     bounds=None, average=None, filters=None,
                     position_field='user_readback', initial_guess=None):
    """
    Maximize a signal with a Lorentzian relationship to a motor

    The following plan does a linear step scan through the parameter space
    while collecting information to create a Lorentzian model. After the scan
    has completed, the created model will be queried to find the estimated
    motor position that will yield the absolute maximum of the Lorentz equation

    Parameters
    ----------
    detector : obj
        The object to be read during the plan

    motor : obj
        The object to be moved via the plan.

    read_field : str
        Field of detector to maximize

    nsteps : int, optional
        The step size used by the initial linear scan to create the Lorentzian
        model. A smaller step size will create a more accurate model, while a
        larger step size will increase the speed of the entire operation.

    bounds : tuple, optional
        The lower and higher limit of the search space. If no value is given
        the :attr:`.limits` property of the motor will be queried next. If this
        does not yield anything useful an exception will be raised

    average : int, optional
        The number of shots to average at every step of the scan. If left as
        None, no average will be used

    filters : dict, optional
        Filters used to drop shots from the analysis

    position_field : str, optional
        Motor field that will have the Lorentzian relationship with the given
        signal

    initial_guess : dict, optional
        Initial guess to the Lorentz model parameters of `sigma` `center`
        `amplitude`
    """
    average = average or 1
    # Define bounds
    if not bounds:
        try:
            bounds = motor.limits
            logger.debug("Bounds were not specified, the area "
                         "between %s and %s will searched",
                         bounds[0], bounds[1])
        except AttributeError as exc:
            raise UndefinedBounds("Bounds are not defined by motor {} or "
                                  "plan".format(motor.name)) from exc
    # Calculate steps
    steps = np.arange(bounds[0], bounds[1], step_size)
    # Include the last step even if this is smaller than the step_size
    steps = np.append(steps, bounds[1])
    # Create Lorentz fit and live model build
    fit    = LorentzianModel(missing='drop')
    i_vars = {'x' : position_field}
    model  = LiveBuild(fit, read_field, i_vars, filters=filters,
                       average=average, init_guess=initial_guess)#,
                       # update_every=len(steps)) # Set to fit only on last step

    # Create per_step plan
    def measure(detectors, motor, step):
        # Perform step
        logger.debug("Measuring average at step %s ...", step)
        yield from checkpoint()
        yield from abs_set(motor, step, wait=True)
        # Measure the average
        return (yield from measure_average([motor, detector],
                                           num=average,
                                           filters=filters))
    # Create linear scan
    plan = list_scan([detector], motor, steps, per_step=measure)

    @subs_decorator(model)
    def inner():
        # Run plan (stripping open/close run messages)
        yield from msg_mutator(plan, block_run_control)

        # Yield result of Lorentz model
        logger.debug(model.result.fit_report())
        max_position = model.result.values['center']

        # Check that the estimated position is reasonable
        if not bounds[0] < max_position  < bounds[1]:
            raise ValueError("Predicted maximum position of {} is outside the "
                             "bounds {}".format(max_position, bounds))
        # Order move to maximum position
        logger.debug("Travelling to maximum of Lorentz at %s", max_position)
        yield from abs_set(motor, model.result.values['center'], wait=True)

    # Run the assembled plan
    yield from inner()
    # Return the fit 
    return model


def rocking_curve(detector, motor, read_field, coarse_step, fine_step,
                  bounds=None, average=None, fine_space=5, initial_guess=None,
                  position_field='user_readback', show_plot=True):
    """
    Travel to the maxima of a bell curve

    The rocking curve scan is two repeated calls of :func:`.maximize_lorentz`.
    The first is a rough step scan which searches the area given by ``bounds``
    using ``coarse_step``, the idea is that this will populate the model enough
    such that we can do a more accurate scan of a smaller region of the search
    space. Once the rough scan is completed, the maxima of the fit is used as
    the center of the new fine scan that probes a region of space with a region
    twice as large as the ``fine_space`` parameter. After this, the motor is
    translated to the calculated maxima of the model

    Parameters
    ----------
    detector : obj
        The object to be read during the plan

    motor : obj
        The object to be moved via the plan.

    read_field : str
        Field of detector to maximize

    coarse_step : float
        Step size for the initial rough scan

    fine_step : float
        Step size for the fine scan

    bounds : tuple, optional
        Bounds for the original rough scan. If not provided, the soft limits of
        the motor are used

    average : int, optional
        Number of shots to average at each step

    fine_space : float, optional
        The amount to scan on either side of the rough scan result. Note that
        the rocking_curve will never tell the secondary scan to travel outside

    position_field : str, optional
        Motor field that will have the Lorentzian relationship with the given
        signal

    initial_guess : dict, optional
        Initial guess to the Lorentz model parameters of `sigma` `center`
        `amplitude`
        of the ``bounds``, so this region may be truncated.

    show_plot : bool, optional
        Create a plot displaying the progress of the `rocking_curve`
    """
    # Define bounds
    if not bounds:
        try:
            bounds = motor.limits
            logger.debug("Bounds were not specified, the area "
                         "between %s and %s will searched",
                         bounds[0], bounds[1])
        except AttributeError as exc:
            raise UndefinedBounds("Bounds are not defined by motor {} or "
                                  "plan".format(motor.name)) from exc
    if show_plot:
        # Create plot
        # subscribe first plot to rough_scan
        pass
    # Run the initial rough scan
    try:
        model = yield from maximize_lorentz(detector, motor, read_field,
                                            step_size=coarse_step,
                                            bounds=bounds, average=average,
                                            position_field=position_field,
                                            initial_guess=initial_guess)
    except ValueError as exc:
        raise ValueError("Unable to find a proper maximum value"
                         "during rough scan") from exc
    # Define new bounds
    center = model.result.values['center']
    bounds = (max(center - fine_space, bounds[0]),
              min(center + fine_space, bounds[1]))

    logger.info("Rough scan of region yielded maximum of %s, "
                "performing fine scan from %s to %s ...",
                center, bounds[0], bounds[1])

    if show_plot:
        # Highlight search space on first plot
        # Subscribe secondary plot
        pass

    # Run the initial rough scan
    try:
        fit = yield from maximize_lorentz(detector, motor, read_field,
                                          step_size=fine_step, bounds=bounds,
                                          average=average,
                                          position_field=position_field,
                                          initial_guess=model.result.values)
    except ValueError as exc:
        raise ValueError("Unable to find a proper maximum value"
                         "during fine scan") from exc

    if show_plot:
        # Draw final calculated max on plots
        pass

    return fit

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

def euclidean_distance(device, device_fields, targets, average=None,
                       filters=None):
    """
    Calculates the euclidean distance between the device_fields and targets.

    Parameters
    ----------
    device : :class:`.Device`
        Device from which to take the value measurements

    device_fields : iterable
        Fields of the device to measure

    targets : iterable
        Target value to calculate the distance from

    average : int, optional
        Number of averages to take for each measurement
    
    Returns
    -------
    distance : float
        The euclidean distance between the device fields and the targets.
    """
    average = average or 1
    # Turn things into lists
    device_fields = as_list(device_fields)
    targets = as_list(targets, len(device_fields))

    # Get the full detector fields
    prep_dev_fields = [field_prepend(fld, device) for fld in device_fields]

    # Make sure the number of device fields and targets is the same
    if len(device_fields) != len(targets): 
        raise ValueError("Number of device fields and targets must be the same."
                         "Got {0} and {1}".format(len(device_fields, 
                                                      len(targets))))
    # Measure the average
    read = (yield from measure_average([device], num=average, filters=filters))
    # Get the squared differences between the centroids
    squared_differences = [(read[fld]-target)**2 for fld, target in zip(
        prep_dev_fields, targets)]
    # Combine into euclidean distance
    distance = math.sqrt(sum(squared_differences))
    return distance
 
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
    indices are the target motor positions.

    Notes
    -----
    Each detector field will be corrected using the corresponding calibration
    motor by index. This means the calibration scan requires the same number of
    detector fields as calibration motors.

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

# def delay_calibration_scan(detector, detector_fields, delay_motor, calib_motors, 
#                            start, stop, steps, first_step=0.1, average=None, 
#                            filters=None, tolerance=.01, delay=None, 
#                            max_steps=None, drop_missing=True, gradients=None, 
#                            *args, **kwargs):
#     """
#     Performs a delay calibration scan on the delay motor
#     """


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
    
