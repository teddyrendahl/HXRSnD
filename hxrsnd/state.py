import logging
from copy import copy

from ophyd.device import Device, ComponentMeta
from super_state_machine.extras import PropertyMachine

logger = logging.getLogger(__name__)


class MachineMeta(ComponentMeta):
    """
    Creates a copied PropertyMachine by inspecting class definition for
    ``machine`` attribute.
    """
    def __new__(cls, name ,bases, clsdict):
        clsobj = super().__new__(cls, name, bases, clsdict)
        #Gather the underlying machine for the 
        if clsdict.get('machine', None):
            machine = copy(clsdict['machine'])
            clsobj.machine = machine
            #Link a copy of the statemachine to new `state` property
            clsobj.state = SubscriptionPropertyMachine(machine)
        else:
            clsobj.state = None
        return clsobj


class SubscriptionPropertyMachine(PropertyMachine):
    """
    Property Machine that runs Ophyd subscriptions

    Expects object to have attribute `machine` that describes states and
    allowed transitions
    """
    def __set__(self, obj, value):
        old_value = self.__get__(obj)
        super().__set__(obj, value)
        value = self.__get__(obj)
        #Run subscription
        obj._run_subs(sub_type=obj.SUB_ST_CH,
                      old_state=old_value,
                      state=value)


class OphydMachine(Device, metaclass=MachineMeta):
    """
    Base implementation of an Ophyd Device backed by a State Machine
    """
    SUB_ST_CH    = 'machine_state_changed'
    _default_sub = SUB_ST_CH

    @classmethod
    def show_states(cls):
        """
        All available states in the machine
        """
        return [state.value for state in cls.machine.States]
