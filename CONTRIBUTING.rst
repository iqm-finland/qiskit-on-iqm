How to develop and contribute
-----------------------------

Qiskit on IQM is an open source Python project.
You can contribute by creating GitHub issues to report bugs or request new features,
or by opening a pull request to submit your own improvements to the codebase.

To start developing the project, clone the
`GitHub repository <https://github.com/iqm-finland/qiskit-on-iqm>`_
and install it in editable mode with all the extras:

.. code-block:: bash

   $ git clone git@github.com:iqm-finland/qiskit-on-iqm.git
   $ cd qiskit-on-iqm
   $ pip install -e ".[dev,docs,testing]"


To be able to build the docs `graphviz <https://graphviz.org/>`_ has to be installed. 
Then to build and view the docs run:

.. code-block:: bash

   $ tox -e docs
   $ firefox build/sphinx/html/index.html


Run the tests:

.. code-block:: bash

   $ tox


Tagging and releasing
---------------------

After implementing changes to Qiskit on IQM one usually wants to release a new version. This means
that after the changes are merged to the main branch

1. the repository should have an updated ``CHANGELOG.rst`` with information about the new changes,
2. the latest commit should be tagged with the new version number,
3. and a release should be created based on that tag.

The last two steps are automated, so one needs to worry only about properly updating the CHANGELOG.
It should be done along with the pull request which is introducing the main changes. The new version
must be added on top of all existing versions and the title must be "Version MAJOR.MINOR", where MAJOR.MINOR
represents the new version number. Please take a look at already existing versions and format the rest of
your new CHANGELOG section similarly. Once the pull request is merged into main, a new tag and a release will
be created automatically based on the latest version definition in the CHANGELOG.
