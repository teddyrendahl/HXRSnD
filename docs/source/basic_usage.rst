===========
Basic Usage
===========

Once the the ``HXRSnD`` module has been installed along with its dependencies,
simply run the shell script in the ``bin`` folder. From the top level of
``HXRSnD`` the command to run is: ::

  ./bin/run_snd

This should set up the ``IPython`` shell with the system instantiated.

Device List
===========
The ``snd`` object is where most if not all of the interfacing with the system
should be done. It has the following devices as attributes:

- ``t1`` - Tower 1 in the split and delay system
- ``t4`` - Tower 4 in the split and delay system
- ``t2`` - Tower 2 in the split and delay system
- ``t3`` - Tower 3 in the split and delay system
- ``di`` - Input diode for the system
- ``dd`` - Diode between the two delay towers
- ``do`` - Output diode for the system
- ``dci`` - Input diode for the channel cut line
- ``dcc`` - Diode between the two channel cut towers
- ``dco`` - Input diode for the channel cut line
- ``E1`` - Macromotor for the delay line energy
- ``E2`` - Macromotor for the channel cut energy
- ``delay`` - Macromotor for the delay
- ``ab`` - Air bearings of the system
- ``daq`` - Object that interfaces with the DAQ

Each of the devices has an assortment of motors that can be viewed from the
'Component' section of the object's docstring. The easiest way to so is by using
the ``IPython``, ``?``, operator.

For convenience, each of the components (except the macromotors) are
instantiated independently and should behave identically to when interfaced
using the ``snd`` object.

Motor and Macromotor Classes
=============================
The basic interface for the Attocube, Aerotech and macromotors were made to be
largely the same, only differing in some of in the implemented convenience
methods. The macromotors currently only have core functionality, but this will
be expanded in the future.

For each of the methods and properties listed below, using the ``?`` operator
will show a more detailed docstring than what is listed below. Also, list of
methods below is not an exhaustive list and is just a catalog of some of (what
my idea are) the more useful methods and attributes.

Methods and Properties Common to All Motors:
--------------------------------------------

- ``motor.move()``, ``motor.mv()`` - Moves the motor to the inputted position.

- ``motor.move_rel()``, ``motor.mvr()`` - Moves the motor by the inputted value.

- ``motor.position``, ``motor.wm()`` - Returns the current position of the motor.

Methods and Properties Common to Aerotech and Attocube Motors
--------------------------------------------------------------

- ``motor.enable()``, ``motor.disable()`` - Enables or disables the motor.

- ``motor.enabled`` - Returns whether the motor is enabled.

- ``motor.stop()`` - Stops the current motor move.

Aerotech Methods and Properties
-------------------------------
- ``motor.offset`` - Current offset of the motor.

- ``motor.offset_position()`` - Sets the current position to be the inputted position by changing the ``motor.offset`` value.

- ``motor.homf()``, ``motor.homr()`` - Homes the motor forward or in reverse.

- ``motor.reconfig()`` - Pulls the motor parameters from the controller.

- ``motor.faulted`` - Returns whether the motor is faulted.

- ``motor.clear()`` - Clears the motor from the faulted state.

- ``motor.state`` - Returns the state PV of the motor (Go, Stop).

- ``motor.ready`` - Returns whether the motor is ready for a motion.

- ``motor.ready_motor()`` - Clears, enabled and changes the state of the motor to "Go".


Attocube Methods and Properties
-------------------------------
- ``motor.connected`` - Returns whether the motor is connected.

- ``motor.refereced`` - Returns whether the motor is referenced.

- ``motor.error`` - Returns whether the motor has an error.

Towers
======
The towers themselves have some methods and attributes that may be useful for
general usage. Below is a list of some of them.

- ``tower.enable()``, ``tower.disable()``, ``tower.clear()`` - Enables, disables or clears all the (aerotech and attocube) motors in this tower.

- ``tower.pos_inserted``, ``tower.pos_removed`` - Attributes that hold the x values that correspond to the inserted and removed positions of the tower.
 
- ``tower.insert()``, ``tower.remove()`` - Moves the tower to the ``pos_inserted`` or ``pos_removed`` positions. *Note*: this only works if ``pos_inserted`` or ``pos_removed`` are set.

- ``tower.energy`` - Sets or returns the energy the tower is currently tuned for based on the angle of the theta motor. *Note*: This is not guaranteed to be correct for now.

- ``tower.theta`` - The bragg angle the tower is currently set to maximize. This is computed using the overall theta motor of the tower (``tower.tth`` for delay towers and ``tower.th`` for the channel cut tower). *Note*: This is not guaranteed to be correct for now.

Bragg Calculations
==================
The bragg angle and energy calculations used to perform the energy macro-motions
are in following script: ::
  
  HXRSnD/hxrsnd/bragg.py

They were both pulled from ``blutil`` and the script should contain all the
necessary components to perform the calculation. For convenience, both
``bragg_angle()`` and ``bragg_energy()`` are imported to this environment for
quick testing.

Additionally, there are three functions implemented by Yanwen that are also
present in the environment. These can be used to perform any quick calculations
and are listed below:

- ``snd_L`` - Calculates the bragg angles for the delay and channel cut branches, in addition to the delay.

- ``snd_diag`` - Calculates the positions of the diagnostic motors in the middle of the system to intersect with the beam at the inputted energies and delay.

- ``snd_delay`` - Calculates the delay of the system based on the length of the delay arm.
