Installation
============

To recreate the HXRSnD environment from scratch, all of the high-level SLAC
packages need to be cloned into the target directory, along with the HXRSnD
repository.

The packages in question are:

- `pswalker <https://github.com/slaclab/pswalker>`_
- `pcds-devices <https://github.com/slaclab/pcds-devices>`_
- `pydm <https://github.com/slaclab/pydm>`_

First create and navigate to a target directory for the new environment: ::

  $ mkdir snd; cd snd

Now clone each of the repos: ::

  $ git clone https://github.com/slaclab/HXRSnD.git
  $ git clone https://github.com/slaclab/pswalker.git
  $ git clone https://github.com/slaclab/pcds-devices.git
  $ git clone https://github.com/slaclab/pydm.git

Now create some soft-links to make operation a little smoother: ::

  $ ln -s HXRSnD/bin/run_snd run_snd              # IPython Launcher
  $ ln -s HXRSnD/screens/run_snd snd_main         # Main SnD Screen
  $ ln -s HXRSnD/scripts.py scripts.py            # Scripts file
  $ ln -s HXRSnD/README.rst README                # Readme file

The launcher script handles linking the repos with the environment, so simply
run the script to get started.
