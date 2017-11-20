=================
Running DAQ Scans
=================
Scans can be run using any of of the HXRSnD motors, including the virtual,
motors using the DAQ. To perform the scans, the ``bluesky`` module is used
meaning scans must be defined as plans that return messages to the ``bluesky``
run engine, indicating the next step in the scan. Once defined, the plans are
passed to the DAQ-configured ``RunEngine`` which will correctly run the DAQ with
the scan.

Defining the Scans
==================

Scans are defined in the ``hxrsnd.plans`` and are imported into the the main
``ipython`` shell for HXRSnD. Using ``linear_scan`` as an example, simply
define the scan as follows: ::

    plan = linear_scan(snd.E2, 9000, 10000, 5, return_to_start=False)

The variable ``plan`` now contains the sequence of steps that will be carried
out during the scan.


Configuring the DAQ
===================

Before any scans can be made, the DAQ must be configured both using normal DAQ
EDM screens, and the python DAQ object.

Overview
--------

Below is a quick list of what must be done to ensure the scan can work properly:

- Restart the DAQ and ensure it is opened properly.
- Select the proper configuration type and select all desired devices.
- Configure the DAQ from python using the following command: ::

    snd.daq.configure()

Below is a list of the basic arguments that can be passed to change the behavior
of the scan: ::
    
- To change the number of events taken at each step in the scan, pass the keyword argument ``events`` to the configure method. For example, the following will set the DAQ to take 1000 events at each step: ::

    snd.daq.configure(events=1000)

- To add a python value to be recorded in the DAQ, pass the keyword argument ``controls`` along with a ``dict`` that has a mapping from name to ``obj``. For example, the following will create DAQ source named "E2" which will contain the channel cut energy: ::

    snd.daq.configure(controls={"E2" : snd.E2})

- To record data, pass the keyword argument ``record`` along with ``True``. For example, to record the data for this run: ::

    snd.daq.configure(record=True)


Running the Scan
================

Once the scan has been instantiated and the DAQ has been configured both in the
EDM screen and python, the scan can simply be passed into the run engine for
execution: ::

  RE_daq(plan)

This should cause the daq to begin taking events at every scan step.

**Note:** Once a plan has been run, it must be redeclared to be run again since
the contents have been consumed.
