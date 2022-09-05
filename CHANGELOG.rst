=========
Changelog
=========

Version 4.4
===========

* Upgrade to iqm-client 7.0. `#24 <https://github.com/iqm-finland/qiskit-on-iqm/pull/24>`_
* Add calibration set ID to result's metadata. `#24 <https://github.com/iqm-finland/qiskit-on-iqm/pull/24>`_

Version 4.3
===========

* ``cortex-cli`` is now the preferred way of authentication.

Version 4.2
===========

* Add optional ``calibration_set_id`` parameter to ``IQMBackend.run``. `#20 <https://github.com/iqm-finland/qiskit-on-iqm/pull/20>`_
* Update documentation regarding the use of Cortex CLI. `#20 <https://github.com/iqm-finland/qiskit-on-iqm/pull/20>`_

Version 4.1
===========

* iqm-client 6.0 support. `#21 <https://github.com/iqm-finland/qiskit-on-iqm/pull/21>`_

Version 4.0
===========

* Remove ``settings_path`` from ``IQMProvider`` and add ``settings`` option to ``IQMBackend.run``. `#17 <https://github.com/iqm-finland/qiskit-on-iqm/pull/17>`_

Version 3.1
===========

* Use metadata returned from iqm-client for minor improvements. `#19 <https://github.com/iqm-finland/qiskit-on-iqm/pull/19>`_

Version 3.0
===========

* Experimental enabling of batch circuit exection. `#18 <https://github.com/iqm-finland/qiskit-on-iqm/pull/18>`_

Version 2.3
===========

* Make ``settings_path`` optional parameter for ``IQMProvider``. `#14 <https://github.com/iqm-finland/qiskit-on-iqm/pull/14>`_
* Requires iqm-client 3.3 if ``settings_path`` is not specified.

Version 2.2
===========

* Use IQM Client's ``get_run_status`` instead of ``get_run`` to retrieve status. `#13 <https://github.com/iqm-finland/qiskit-on-iqm/pull/13>`_
* Requires iqm-client 3.2

Version 2.1
===========

* Allow serialization of ``barrier`` operations. `#12 <https://github.com/iqm-finland/qiskit-on-iqm/pull/12>`_

Version 2.0
===========

* Update user authentication to use access token. `#11 <https://github.com/iqm-finland/qiskit-on-iqm/pull/11>`_
* Upgrade IQMClient to version >= 2.0 `#11 <https://github.com/iqm-finland/qiskit-on-iqm/pull/11>`_

Version 1.1
===========

* Fix code examples in `user guide <https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html>`_, add missing dependency in `developer guide <https://github.com/iqm-finland/qiskit-on-iqm/blob/main/CONTRIBUTING.rst>`_. `#8 <https://github.com/iqm-finland/qiskit-on-iqm/pull/8>`_

Version 1.0
===========

* Updated documentation layout to use sphinx-book-theme. `#6 <https://github.com/iqm-finland/qiskit-on-iqm/pull/6>`_

Version 0.2
===========

* Publish ``qiskit_iqm``. `#4 <https://github.com/iqm-finland/qiskit-on-iqm/pull/4>`_
* Implement functionality to serialize compatible circuits, send for execution and parse returned results. `#3 <https://github.com/iqm-finland/qiskit-on-iqm/pull/3>`_


Version 0.1
===========

* Project skeleton created.
