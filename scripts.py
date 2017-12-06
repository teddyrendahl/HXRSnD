#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to hold temporary routines created during the beamtime.

Everything added here is star (*) imported into the IPython shell after the
``SplitAndDelay`` object has succesfully instantiated. Therefore, it is 
recommended to run the specific unit-test to quickly ensure your inserted code 
is syntactically correct. More specifically, it will test if this script is 
importable. Of course this will not guarantee that the code works as intended,
but it will pick up on any 'easy' mistakes, like a mismatched parenthesi. To run
the test, in the top level directory, first source the snd environment:

    source snd_env.sh

Then run the pytest script with the following command:

    python run_tests.py hxrsnd/tests/test_scripts.py

The script will run (at least) one test and if your code was written correctly,
it will pass.
"""
############
# Standard #
############
# Imports from the Python standard library go here
import logging

###############
# Third Party #
###############
# Imports from the third-party modules go here
import numpy as np

########
# SLAC #
########
# Imports from other SLAC modules go here

##########
# Module #
##########
# Imports from the HXRSnD module go here
import hxrsnd

# Default logger
logger = logging.getLogger(__name__)

################################################################################
#                            Good Design Practices                             #
################################################################################

# #       Replace all print() statements with logger.info() statements       # #
################################################################################

# The Main reason for this is the IPython shell will log everything you log in
# log files IFF you use the logger methods, while also printing to the console.
# Even better, is if you include various logger levels. To use the logger, 
# simply make the following substitution:

#   print("text") -->  logger.info("text")

# It is that simple, that the message will now be archived in the info level
# (HXRSnD/logs/info.log) and debug level (HXRSnD/logs/debug.log) log files.

# #                              Leave Comments                              # #
################################################################################

# This seems like it may not be that important, but the purpose of this file is
# to temporarily hold scripts developed during beamtime to then be migrated by
# us (PCDS) into the module. By leaving comments, you make it easier for 
# everyone to understand what the code is doing. 


################################################################################
#                              Insert Code Below                               #
################################################################################










