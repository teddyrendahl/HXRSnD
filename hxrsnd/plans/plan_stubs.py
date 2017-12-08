"""
Small plans used in HXRSnD
"""
############
# Standard #
############
import logging
import math 

###############
# Third Party #
###############

########
# SLAC #
########
from pswalker.utils             import field_prepend
from pswalker.plans             import measure_average

##########
# Module #
##########
from ..utils import as_list

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
