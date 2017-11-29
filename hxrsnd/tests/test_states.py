############
# Standard #
############
import logging
from enum import Enum

###############
# Third Party #
###############
import pytest
from super_state_machine.machines import StateMachine
from super_state_machine.errors   import TransitionError
##########
# Module #
##########
from hxrsnd.state import OphydMachine

logger = logging.getLogger(__name__)

class PuckStateMachine(StateMachine):
    """
    Mock PuckStateMachine
    """
    class States(Enum):
        """state.name = state.value"""
        GLIDING = 'gliding'
        FLYING  = 'flying'
        LANDED  = 'landed'
        LOCKED  = 'locked'

        @classmethod
        def states(cls):
            return [state.value for state in cls]

    class Meta:
        initial_state = 'landed'
        transitions = {
                'locked'  : ['landed'],
                'landed'  : ['locked', 'flying'],
                'flying'  : ['landed', 'gliding'],
                'gliding' : ['flying']}

#Fake Puck Class
class Puck(OphydMachine):
    machine  = PuckStateMachine
    readback = None
    def __init__(self, prefix, name=None, *args, **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)


def test_ophydmachine_creation():
    Puck.show_states() == ['locked', 'landed', 'flying', 'gliding']


def test_ophydmachine_subscription():
    #Initialize puck and lock
    puck = Puck("Tst:Puck")
    puck.state = 'locked'
    #Callback to update readback
    def update_state(*args, state=None, obj=None, **kwargs):
        logger.debug("Updating {} readback to {}".format(obj, state))
        if state and obj:
            obj.readback = state
    #Subscribe to changes
    puck.subscribe(update_state, run=True)
    #Assert that the device initalizes correctly
    assert puck.readback == 'locked'
    #Assert changes are tracked when state changes
    puck.state = 'landed'
    assert puck.readback == 'landed'
    #Try a bad transition and make sure our readback stays put
    try:
        puck.state = 'gliding'
    except TransitionError:
        pass
    assert puck.readback == 'landed'

