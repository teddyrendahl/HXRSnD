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
from lmfit.models       import LorentzianModel
from pswalker.callbacks import LiveBuild
from pswalker.plans     import measure_average
from bluesky            import Msg
from bluesky.plans      import msg_mutator, scan, abs_set, checkpoint
from bluesky.plans      import subs_decorator

##########
# Module #
##########
from .errors import UndefinedBounds

logger = logging.getLogger(__name__)

def block_run_control(msg):
    """
    Block open and close run messages
    """
    if msg.command in ['open_run', 'close_run']:
        return None

    return msg


def maximize_lorentz(detector, motor, read_field, nsteps=10,
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
    #Define bounds
    if not bounds:
        try:
            bounds = motor.limits
            logger.debug("Bounds were not specified, the area "
                         "between %s and %s will searched",
                         bounds[0], bounds[1])
        except AttributeError as exc:
            raise UndefinedBounds("Bounds are not defined by motor %s or "
                                  "plan".format(motor.name)) from exc

    #Create Lorentz fit and live model build
    fit    = LorentzianModel(missing='drop')
    i_vars = {'x' : position_field}
    model  = LiveBuild(fit, read_field, i_vars, filters=filters,
                       average=average, init_guess=initial_guess,
                       update_every=nsteps) #Set to fit only on last step

    #Create per_step plan
    def measure(detectors, motor, step):
        #Perform step
        logger.debug("Measuring average at step %s ...", step)
        yield from checkpoint()
        yield from abs_set(motor, step, wait=True)
        #Measure the average
        return (yield from measure_average([motor, detector],
                                           num=average,
                                           filters=filters))

    #Create linear scan
    plan = scan([detector], motor, bounds[0], bounds[1],
                nsteps, per_step=measure)

    @subs_decorator(model)
    def inner():
        #Run plan (stripping open/close run messages)
        yield from msg_mutator(plan, block_run_control)

        #Yield result of Lorentz model
        logger.debug(model.result.fit_report())
        max_position = model.result.values['center']

        #Check that the estimated position is reasonable
        if not bounds[0] < max_position  < bounds[1]:
            raise ValueError("Predicted maximum position of {} is outside the "
                             "bounds {}".format(max_position, bounds))

        #Order move to maximum position
        logger.info("Travelling to maximum of Lorentz at %s", max_position)
        yield from abs_set(motor, model.result.values['center'], wait=True)

    yield from inner()
