#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exceptions for the SnD system.
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############

########
# SLAC #
########

##########
# Module #
##########

# Exceptions

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


class BadN2Pressure(SndException):
    """
    Exception raised when an action requiring the N2 pressure be good is 
    requested with a bad pressure.
    """
    pass
