=============
Running Scans
=============

Scans can be run using any of of the HXRSnD motors, including the virtual,
motors using the DAQ. To perform the scans, the ``bluesky`` module is used
meaning scans must be defined as plans that return messages to the ``bluesky``
run engine, indicating the next step in the scan.

For a comprehensive tutorial on how to write ``bluesky`` plans, see their
documentation on `Basic Usage & Intro to Plans. <https://nsls-ii.github.io/bluesky/plans_intro.html>`_

Defining Plans
==============

Scans are defined in the ``hxrsnd.plans`` script and are imported into the the
main ``IPython`` shell for HXRSnD. Using ``linear_scan`` as an example, define
the plan as follows: ::

  In [1]: plan = linear_scan(snd.E2, 9000, 10000, 5, return_to_start=False, verify_move=False)

The variable ``plan`` now contains the sequence of steps that will be carried
out to perform the scan using the ``E2`` macromotor.

Running Plans
=============

To actually run the scan, it must be passed to a ``bluesky``  ``RunEngine``
object. In the SnD ``IPython`` shell, there is a ``RunEngine`` object defined as
``RE``. So to run the aforementioned scan: ::

  In [2]: RE(plan)


