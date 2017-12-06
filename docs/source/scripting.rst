Adding Scripts
==============

If new functions, classes, objects, etc. need to be injected into the
environment, the best place to put them is in the ``HXRSnD/scripts.py`` file.
The contents of this file are star (*) imported into the SnD ``IPython``
environment after the ``snd`` object has been instantiated.

Testing New Scripts
-------------------

If new code is added to this file, it is advisable that you run the ``pytest``
test that ensures importability. To run the test, in the top level directory,
first source the snd environment: ::

    $ source snd_env.sh

Then run the ``pytest`` script with the following command: ::

    $ python run_tests.py hxrsnd/tests/test_scripts.py

The script will run (at least) one test and if your code was written correctly,
it will pass.

.. note:: Passing the test does not guarantee the code works as indended, just
          that it is syntactically correct.
