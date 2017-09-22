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

class SnDException(Exception):
    """
    Base aerotech motor exceptions.
    """
    pass


class MotorDisabled(SnDException):
    """
    Exception raised when an action requiring the motor be enabled is requested.
    """
    pass


class MotorFaulted(SnDException):
    """
    Exception raised when an action requiring the motor not be faulted is 
    requested.
    """
    pass


class MotorError(SnDException):
    """
    Exception raised when an action requiring the motor not have an error is 
    requested.
    """
    pass


class BadN2Pressure(SnDException):
    """
    Exception raised when an action requiring the N2 pressure be good is 
    requested with a bad pressure.
    """
    pass
