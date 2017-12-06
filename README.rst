====================================================================
Welcome to the Hard X-Ray Split and Delay Automated Controls System!
====================================================================
.. image:: https://travis-ci.org/slaclab/HXRSnD.svg?branch=master
    :target: https://travis-ci.org/slaclab/HXRSnD

.. image:: https://codecov.io/gh/slaclab/HXRSnD/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/slaclab/HXRSnD

.. image:: https://landscape.io/github/slaclab/HXRSnD/master/landscape.svg?style=flat
   :target: https://landscape.io/github/slaclab/HXRSnD/master

Controls automation module for the hard x-ray split and delay instrument.

Getting Started
===============

The easiest way to start using the hard x-ray split and delay is to navigate to
the released area which has everything setup. From any of the LCLS NFS machines
that can view XCS PVs, run the following to change to the correct directory: ::

  $ cd /reg/neh/operator/xcsopr/bin/snd

From here, all the core functionality of the split and delay system can be
accessed.

Running the IPython Shell
-------------------------

The most common used way to interface with the system is through the ``IPython``
shell. From the top level SnD directory listed above, run the following launcher
script: ::

  $ ./run_snd

The shell will have all the SnD objects instantiated and ready for use.

.. note:: This is a softlink to the launcher script which lives in
          ``HXRSnD/bin/``

Instrument Screens
------------------

There is a system level EDM screen that has all the motors and pneumatics. To
launch the screen, run the following launcher sript from the directory listed
above: ::

  $ ./snd_main  

.. note:: This is a softlink to the launcher script which lives in
          ``HXRSnD/screens/``
  
To view diode correlation plots, run the following launcher script from the
directory listed above: ::

  $ ./show_diodes.sh

