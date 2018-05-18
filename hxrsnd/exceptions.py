#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exceptions for the SnD system.
"""

import logging

logger = logging.getLogger(__name__)

# Exceptions

class InputError(Exception):
    """
    Exception when the inputs to a function or method are invalid.
    """
    pass


class UndefinedBounds(Exception):
    """
    Exception when bounds of plan are not defined
    """
    pass


class SndException(Exception):
    """
    Base aerotech motor exceptions.
    """
    pass


class MotorDisabled(SndException):
    """
    Exception raised when an action requiring the motor be enabled is requested.
    """
    pass


class MotorFaulted(SndException):
    """
    Exception raised when an action requiring the motor not be faulted is 
    requested.
    """
    pass


class MotorError(SndException):
    """
    Exception raised when an action requiring the motor not have an error is 
    requested.
    """
    pass


class MotorStopped(SndException):
    """
    Exception raised when an action requiring the motor to not be stopped is 
    requested.
    """
    pass


class BadN2Pressure(SndException):
    """
    Exception raised when an action requiring the N2 pressure be good is 
    requested with a bad pressure.
    """
    pass
