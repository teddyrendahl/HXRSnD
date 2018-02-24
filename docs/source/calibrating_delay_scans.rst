=======================
Calibrating Delay Scans
=======================

Performing uncalibrated scans using the ``delay`` macromotor results in
positional instability of the beam at the sample. To address this, ``delay`` has
several methods to characterize and correct the scan.

Characterizing Beam Instability
===============================

centroid_scan

graphing 

Calibration Operations
======================

has_calibration and use_calibration

New calibration

saving a calibration

loading a calibration


Inspecting the Calibration
==========================


Modifying Calibrations
======================

Changing post processing

Rescaling a calibration


Example Workflow
================

Say we want to perform a corrected scan with the the ``delay`` macromotor using
``linear_scan`` from a position ``start`` to a position ``stop``, taking
``steps`` number of steps in between. First check if there is an existing
correction table and if it is


Characterizing 
===============
