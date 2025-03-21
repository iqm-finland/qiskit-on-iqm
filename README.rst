|CI badge| |Release badge| |Black badge|

.. |CI badge| image:: https://github.com/iqm-finland/qiskit-on-iqm/actions/workflows/ci.yml/badge.svg
.. |Release badge| image:: https://img.shields.io/github/release/iqm-finland/qiskit-on-iqm.svg
.. |Black badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

Qiskit on IQM
#############

**The** ``qiskit-iqm`` **package is deprecated and the GitHub repository has been archived. New versions of
Qiskit on IQM will be published as part of the** `iqm-client <https://pypi.org/project/iqm-client/>`_
**package and can be installed from public PyPI with** ``pip install iqm-client[qiskit]``.
**See the latest documentation at** `<https://docs.meetiqm.com/iqm-client/user_guide_qiskit.html>`_ **for more
information. The source code is available as part of the** ``iqm-client`` **package and a public mirror of the source
code is available at** `<https://github.com/iqm-finland/sdk>`_. **For support, you can contact support@meetiqm.com**.

`Qiskit <https://qiskit.org/>`_ adapter for `IQM's <https://www.meetiqm.com>`_ quantum computers.


What is it good for?
====================

With Qiskit on IQM, you can for example:

* Transpile arbitrary quantum circuits for IQM quantum architectures
* Simulate execution with an IQM-specific noise model
* Run quantum circuits on an IQM quantum computer


Installation
============

The recommended way is to install the distribution package ``qiskit-iqm`` directly from the
Python Package Index (PyPI):

.. code-block:: bash

   $ pip install qiskit-iqm


Documentation
=============

The documentation of the latest Qiskit on IQM release is available
`here <https://iqm-finland.github.io/qiskit-on-iqm/index.html>`_.

Jump to our `User guide <https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html>`_
for a quick introduction on how to use Qiskit on IQM.

You can build documentation for any older version locally by cloning the Git repository, checking out the
corresponding tag, and running the docs builder. For example, to build the documentation for version ``12.2``:

.. code-block:: bash

    $ git clone git@github.com:iqm-finland/qiskit-on-iqm.git
    $ cd qiskit-on-iqm
    $ git checkout 12.2
    $ tox run -e docs

``tox run -e docs`` will build the documentation at ``./build/sphinx/html``. This command requires the ``tox,``, ``sphinx`` and
``sphinx-book-theme`` Python packages (see the ``docs`` optional dependency in ``pyproject.toml``);
you can install the necessary packages with ``pip install -e ".[dev,docs]"``


Copyright
=========

Qiskit on IQM is free software, released under the Apache License, version 2.0.

Copyright 2022-2024 Qiskit on IQM developers.
