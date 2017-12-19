#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to hold temporary routines created during the beamtime.

Everything added here is star (*) imported into the IPython shell after the
``SplitAndDelay`` object has succesfully instantiated. Therefore, it is
recommended to run the specific unit-test to quickly ensure your inserted code
is syntactically correct. More specifically, it will test if this script is
importable. Of course this will not guarantee that the code works as intended,
but it will pick up on any 'easy' mistakes, like a mismatched parenthesi. To
run the test, in the top level directory, first source the snd environment:

    source snd_env.sh

Then run the pytest script with the following command:

    python run_tests.py hxrsnd/tests/test_scripts.py

The script will run (at least) one test and if your code was written correctly,
it will pass.
"""
# Imports from the Python standard library go here
import logging

# Imports from the third-party modules go here
import numpy as np
from ophyd import Device, EpicsSignal, Component as Cmp
from ophyd.sim import hw
from ophyd.status import wait as status_wait

# Imports from other SLAC modules go here

# Imports from the HXRSnD module go here
import snd_devices

# Default logger
logger = logging.getLogger(__name__)

###############################################################################
#                           Good Design Practices                             #
###############################################################################

# #      Replace all print() statements with logger.info() statements       # #
###############################################################################

# The Main reason for this is the IPython shell will log everything you log in
# log files IFF you use the logger methods, while also printing to the console.
# Even better, is if you include various logger levels. To use the logger,
# simply make the following substitution:

#   print("text") -->  logger.info("text")

# It is that simple, that the message will now be archived in the info level
# (HXRSnD/logs/info.log) and debug level (HXRSnD/logs/debug.log) log files.

# #                             Leave Comments                              # #
###############################################################################

# This seems like it may not be that important, but the purpose of this file is
# to temporarily hold scripts developed during beamtime to then be migrated by
# us (PCDS) into the module. By leaving comments, you make it easier for
# everyone to understand what the code is doing.


###############################################################################
#                             Insert Code Below                               #
###############################################################################
hw = hw()  # Fake hardware for testing
fake_motor = hw.motor


class NotepadScanStatus(Device):
    istep = Cmp(EpicsSignal, ":ISTEP")
    isscan = Cmp(EpicsSignal, ":ISSCAN")
    nshots = Cmp(EpicsSignal, ":NSHOTS")
    nsteps = Cmp(EpicsSignal, ":NSTEPS")
    var0 = Cmp(EpicsSignal, ":SCANVAR00")
    var1 = Cmp(EpicsSignal, ":SCANVAR01")
    var2 = Cmp(EpicsSignal, ":SCANVAR02")
    var0_max = Cmp(EpicsSignal, ":MAX00")
    var1_max = Cmp(EpicsSignal, ":MAX01")
    var2_max = Cmp(EpicsSignal, ":MAX02")
    var0_min = Cmp(EpicsSignal, ":MIN00")
    var1_min = Cmp(EpicsSignal, ":MIN01")
    var2_min = Cmp(EpicsSignal, ":MIN02")

    def clean_fields(self):
        for sig_name in self.signal_names:
            sig = getattr(self, sig_name)
            val = sig.value
            if isinstance(val, (int, float)):
                sig.put(0)
            elif isinstance(val, str):
                sig.put('')


notepad_scan_status = NotepadScanStatus('XCS:SCAN', name='xcs_scan_status')


def ascan(motor, start, stop, num, events_per_point=360, record=False,
          controls=None, **kwargs):
    """
    Quick re-implementation of old python for the transition
    """
    daq = snd_devices.daq
    events = events_per_point
    status = notepad_scan_status
    status.clean_fields()
    if controls is None:
        controls = {}

    def get_controls(motor, extra_controls):
        out_arr = {motor.name: motor}
        out_arr.update(extra_controls)
        return out_arr

    try:
        scan_controls = get_controls(motor, controls)
        daq.configure(record=record, controls=scan_controls)

        status.isscan.put(1)
        status.nshots.put(events_per_point)
        status.nsteps.put(num)
        status.var0.put(motor.name)
        status.var0_max.put(max((start, stop)))
        status.var0_min.put(min((start, stop)))

        for i, step in enumerate(np.linspace(start, stop, num)):
            logger.info('Beginning step {}'.format(step))
            mstat = motor.set(step, **kwargs)
            status.istep.put(i)
            status_wait(mstat)
            scan_controls = get_controls(motor, controls)
            daq.begin(events=events, controls=scan_controls)
            logger.info('Waiting for {} events ...'.format(events))
            daq.wait()
    finally:
        logger.info('DONE!')
        status.clean_fields()
        daq.end_run()
        daq.disconnect()
