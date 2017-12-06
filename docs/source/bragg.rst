============
Calculations
============

The bragg angle and energy calculations used to perform the energy macro-motions
are in following script: ::
  
  HXRSnD/hxrsnd/bragg.py

Bragg Calculations
------------------

Both the angle and energy calculations were  pulled from ``blutil`` and the
script should contain all the necessary components to perform the calculation.

.. autofunction:: hxrsnd.bragg.bragg_angle

.. autofunction:: hxrsnd.bragg.bragg_energy
                  

Macro-motion Calculations
-------------------------

There are three functions that perform the same calculations used in for the
macromotors. These were used to used to perform quick position verification.

.. autofunction:: hxrsnd.bragg.snd_L

.. autofunction:: hxrsnd.bragg.snd_diag

.. autofunction:: hxrsnd.bragg.snd_delay             
