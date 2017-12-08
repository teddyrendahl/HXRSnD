===============
Alignment Plans
===============

Running the Rocking Curve
-------------------------
The rocking curve does two successive step scans, using the maximum of the
first to center the finer scan on the second. There are a number of fields to
configure and play with but lets start simple:

.. code:: python

   rock = rocking_curve(wave8.diode_1, hxrsnd.th2, 'peakT', 1, 0.1,
                        bounds=(0, 20), average=100)

   RE(rock)

The code above runs a step scan from 0 to 20 in steps of 1, reading the diode
at each point. A fit is processed at the end and a second scan is started 5
units to the left of the calculated center and runs using 0.1 as the step size
until we reach 5 units greater than our first result. Finally, the rotation
axis is centered with our new maximum. 

If you want to use change the range of the second finer scan, you can use the
`fine_space` keyword. In addition, the `lmfit` model that does our fitting
accepts an initial guess. This can be useful to make an assumption about the
system to improve the accuracy and dependability of the scan. Using this
parameter would look like:

.. code:: python
   rock = rocking_curve(wave8.diode_1, hxrsnd.th2, 'peakT', 1, 0.1,
                        bounds=(0, 20), average=100,
                        initial_guess = {'sigma' : 1.0,
                                         'center' : 10.0,
                                         'amplitude' : 1220.4})

   RE(rock)


Documentation
-------------
.. autofunction:: hxrsnd.plans.alignment.rocking_curve

.. autofunction:: hxrsnd.plans.alignment.maximize_lorentz
