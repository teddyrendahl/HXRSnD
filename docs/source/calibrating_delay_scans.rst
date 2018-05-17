=======================
Calibrating Delay Scans
=======================

Performing uncalibrated scans using the ``delay`` macromotor results in
positional instability of the beam at the sample. To address this, ``delay`` has
several methods to characterize and correct the scan.

.. warning:: The functionality described here has not been commissioned, and
             should be used with caution.

Characterizing Beam Instability
===============================

The main way to characterize the current scan instability is to run the
``centroid_scan`` method. The method performs a scan using the inputted scan
parameters, measuring the centroids of the beam at Opal 1. The results are then
saved and graphed for the user to see. ::

  In [1]: snd.delay.centroid_scan(start, stop, step)

To view the centroids again after the scan has been completed, the method
``view_centroids`` can be used to view the centroids from the most recent
``centroids_scan``. ::

  In [2]: snd.delay.view_centroids()

To view the graph displayed after the scan, run the ``graph_centroids`` method.
::

  In [3]: snd.delay.graph_centroids()

.. note:: The results shown by ``view_centroids`` and ``graph_centroids`` come
          from the recent centroid scan or calibration. Anytime a new centroid
          scan is run, the previous scan data is overwritten.

Calibration Operations
======================

In the event ``centroid_scan`` reveals the beam drifts too much throughout the
scan, there is a routine for building a correction table using the
``snd.t1.chi1`` and ``snd.t1.y1`` motors to correct for the x and y centroids
respectively. This correction table is put together using the table generated
from a ``centroid_scan`` along with parameters to find the scaling information
between each of the motor positions and the beam centroids. Together all the
information collected during a ``calibrate`` run, constitutes a specific
calibration.

High-Level Properties
---------------------

The ``delay`` macromotor comes with two high level properties pertaining to the
current state of the calibration. ``has_calibration`` indicates that a properly
configured calibration is currently loaded to the motor, simply returning a
``bool``.

The second high level property is ``use_calibration`` which determines whether
a calibration should be used during a move. By default, anytime a calibration is
created or loaded, ``use_calibration`` is set to be ``True``. However, this is
primarily useful if there is a move where performing a the correction is not
desired. By setting ``use_calibration`` to ``False`` all moves will be done
without corrections

.. note:: Motor corrections will only be performed on every ``move`` command if
          both ``has_calibration`` and ``use_calibration`` are ``True``.

Creating a New Calibration
--------------------------

If a new calibration is necessary, the entire calibration routine can be run
using the ``calibrate`` method along with the desired scan parameters. ::

  In [1]: snd.delay.calibrate(start, stop, step)

The calibration routine itself consists of first performing a centroid scan to
measure the current beam drift, and then performing a walk using each of the
calibration motors to find the motor position to centroid scaling. Once,
complete, the motor will automatically start using the new calibration for all
subsequent ``move`` commands. Additionally, all the motors will be returned to
their original positions after the routine has completed.

.. note:: A confirmation to overwrite the existing calibration will be required
          to run ``calibrate`` if the motor already has a valid configuration.

Saving and Loading Calibrations
-------------------------------

Calibrations used for the ``delay`` motor are all saved in the
``HXRSnD/calibrations`` directory. Whenever a ``calibration`` routine has
completed, the calibration is saved into a file named
``current_calibration.json``. To save a calibration more permanently, the
method ``save_calibration`` can be used by passing a either filename or a full
path. Running, ::

  In [1]: snd.delay.save_calibration('my_calibration')

Will save the current calibration as
``HXRSnD/calibrations/my_calibration.json``. 

To load this configuration, the ``load_calibration`` method takes calibration
names, searches the ``HXRSnD/calibrations`` directory, and then applies the
dound calibration. For example, ::

  In [2]: snd.delay.load_calibration('my_calibration')

loads the ``my_calibration.json`` from ``HXRSnD/calibrations``.

.. note:: Running ``load_calibration`` without any inputs automatically loads
          ``current_calibration.json``.

Inspecting the Calibration
==========================

To view the contents of a calibration, the ``calibration`` property returns a
dictionary with five keys:

- calib : ``DataFrame`` containing the correction table used by the
  calibration motors.
- motors : List of ``Motor`` objects that refer to the motors used by the
  calibration.
- scan : ``DataFrame`` containing the results of the centroid scan used to
  build the correction table.
- scale : List if values in units of ps/pixel, used to convert between pixel
  positions and delay position.
- start : List of starting positions of the motors used to calculate the scale.

.. note:: ``calibration`` is a read-only property and cannot be used to modify
          the live calibration.
  
Modifying Calibrations
======================

Each of the five calibration values listed above can be modified outright using
the ``configure`` method. This is done by running ``configure`` and passing the
desired change as a keyword argument.

.. warning:: It is not advisable to change the the calibration in ways not
             listed below. 

Correction Table Post-Processing
--------------------------------

A simple reason to modify the correction table would be to apply some level of
post processing to the resulting table. For example, to apply a Savitzky-Golay
smoothing filter, first capturet he current correction table in a new dataframe
using the ``calibration`` property, ::

  In [1]: df_calib = snd.delay.calibration['calib']

Then create a new dataframe with the applied filter using some ``window_length``
and ``polyorder`` (see documentation on ``scipy.signal.savgol_filter`` for more
details), ::

  In [2]: df_savgol = df_calib.apply(savgol_filter, args=(window_length, polyorder))

And then configure the motor to use this new correction table, ::

  In [3]: snd.delay.configure(calib=df_savgol)
  
.. note:: Whenever the correction table is modified using ``configure``, the
          number of columns must equal the number of motors listed in
          ``snd.delay.calibration['motors']``.

Rescaling the Correction Table
------------------------------

In the event that the picosecond per pixel scaling factor may need to be redone,
the method ``rescale_calibration`` will perform the scaling routine and then
update the calibration accordingly. ::

  In [1]: snd.delay.rescale_calibration()
