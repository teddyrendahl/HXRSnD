Welcome to the Hard X-Ray Split and Delay Alignment System!
===========================================================
.. image:: https://travis-ci.org/slaclab/HXRSnD.svg?branch=master
    :target: https://travis-ci.org/slaclab/HXRSnD

.. image:: https://codecov.io/gh/slaclab/HXRSnD/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/slaclab/HXRSnD

.. image:: https://landscape.io/github/slaclab/HXRSnD/master/landscape.svg?style=flat
   :target: https://landscape.io/github/slaclab/HXRSnD/master
Beam Alignment module for the hard x-ray split and delay.

===================================
Split and Delay IPython Environment
===================================

Basic readme file for getting started with the Split and Delay `ipython` shell.
Its main object of interest is `snd` which contains all the various towers and
diagnostics along with their respective motors, as well as pseudomotors that
control the system energy and delay.

Getting Started
===============
Once the the `HXRSnD` module has been installed along with its dependencies,
simply run the shell script in the `bin` folder. From the top level of `HXRSnD`
the command to run is: ::

  ./bin/run_snd

This should set up the `ipython` shell with the system instantiated.

Basic Usage
===========
The `snd` object is where most if not all of the interfacing with the system
should be done. It has the following devices as attributes:
 - `t1` - Tower 1 in the split and delay system
 - `t4` - Tower 4 in the split and delay system
 - `t2` - Tower 2 in the split and delay system
 - `t3` - Tower 3 in the split and delay system
 - `di` - Input diode for the system
 - `dd` - Diode between the two delay towers
 - `do` - Output diode for the system
 - `dci` - Input diode for the channel cut line
 - `dcc` - Diode between the two channel cut towers
 - `dco` - Input diode for the channel cut line
 - `E1` - Pseudomotor for the delay line energy
 - `E2` - Pseudomotor for the channel cut energy
 - `E` - Pseudomotor for the system energy (delay and channel cut together)
 - `delay` - Pseudomotor for the delay

Each of the devices has an assortment of motors that can be viewed from the
'Component' section of the object's docstring. The easiest way to so is by using
the `ipython`, `?`, operator.

For example, to view the components of `snd.t2`: ::

    In [1]: snd.t2?
    Type:        ChannelCutTower
    String form: ChannelCutTower(prefix='XCS:SND:T2', name='XCS:SND_t2', parent='XCS:SND', read_attrs=['th', 'x'], configuration_attrs=[])
    File:        /reg/neh/home5/apra/work/python/snd/HXRSnD/hxrsnd/devices.py
    Docstring:  
    Channel Cut tower.

    Components
    ----------
    th : RotationAero
	Rotation stage of the channel cut crystal

    x : LinearAero
	Translation stage of the tower

Which shows that the `snd.t2` has two motors `th` and `x` which can be accessed
using `snd.t2.th` and `snd.t2.x` respectively.

For convenience, each of the components (except the pseudomotors) are
instantiated independently and should behave identically to when interfaced
using the `snd` object.

Motor and Pseudomotor Classes
=============================
The basic interface for the Attocube, Aerotech and pseudomotors were made to be
largely the same, only differing in some of in the implemented convenience
methods. The pseudomotors currently only have core functionality, but this will
be expanded in the future.

For each of the methods and properties listed below, using the `?` operator will
show a more detailed docstring than what is listed below. Also, list of methods
below is not an exhaustive list and is just a catalog of some of (what my idea
are) the more useful methods and attributes.

Methods common to all motors:
------------------------------
`motor.move()`, `motor.mv()`
 - Moves the motor to the inputted position.

`motor.move_rel()`, `motor.mvr()`
 - Moves the motor by the inputted value.

`motor.position`, `motor.wm`
 - Returns the current position of the motor.

Methods common to Aerotech and Attocube Motors
----------------------------------------------

`motor.enable()`, `motor.disable()`
 - Enables or disables the motor.

`motor.enabled`
 - Returns whether the motor is enabled.

`motor.stop()`
 - Stops the current motor move.

Aerotech Methods
----------------
`motor.offset`
 - Current offset of the motor.

`motor.offset_position()`
 - Sets the current position to be the inputted position by changing the `motor.offset` value.

`motor.homf()`, `motor.homr()`
 - Homes the motor forward or in reverse.

`motor.reconfig()`
 - Pulls the motor parameters from the controller.

`motor.faulted`
 - Returns whether the motor is faulted.

`motor.clear()`
 - Clears the motor from the faulted state.

Attocube Methods
----------------
`motor.connected`
 - Returns whether the motor is connected.

`motor.refereced`
 - Returns whether the motor is referenced.

`motor.error`
 - Returns whether the motor has an error.

Towers
======
The towers themselves have some methods and attributes that may be useful for
general usage. Below is a list of some of them.

`tower.enable()`, `tower.disable()`, `tower.clear()`
 - Enables, disables or clears all the (aerotech and attocube) motors in this tower.

`tower.pos_inserted`, `tower.pos_removed`
 - Attributes that hold the x values that correspond to the inserted and removed positions of the tower.
 
`tower.insert()`, `tower.remove()`
 - Moves the tower to the `pos_inserted` or `pos_removed` positions. *Note*: this only works if `pos_inserted` or `pos_removed` are set.

`tower.energy`
 - Sets or returns the energy the tower is currently tuned for based on the angle of the theta motor. *Note*: This is not guaranteed to be correct for now.

`tower.theta`
 - The bragg angle the tower is currently set to maximize. This is computed using the overall theta motor of the tower (`tower.tth` for delay towers and `tower.th` for the channel cut tower). *Note*: This is not guaranteed to be correct for now.

Bragg Calculations
==================
The bragg angle and energy calculations used to perform the energy macro-motions
are in following script: ::

  HXRSnD/hxrsnd/bragg.py

They were both pulled from `blutil` and the script should contain all the
necessary components to perform the calculation. For convenience, both
`bragg_angle()` and `bragg_energy()` are imported to this environment for
quick testing.

Additionally, there are three functions implemented by Yanwen that are also
present in the environment. These can be used to perform any quick calculations
and are listed below:

`snd_L`
- Calculates the bragg angles for the delay and channel cut branches, in addition to the delay.

`snd_diag`
- Calculates the positions of the diagnostic motors in the middle of the system to intersect with the beam at the inputted energies and delay.

`snd_delay`
- Calculates the delay of the system based on the length of the delay arm.
