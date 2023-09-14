=========
Changelog
=========

Version 11.0
============

* Move ``qiskit_iqm`` package to ``iqm`` namespace. `#79 <https://github.com/iqm-finland/qiskit-on-iqm/pull/79>`_

Version 10.11
=============

* Update user guide with information of execution timestamps. `#78 <https://github.com/iqm-finland/qiskit-on-iqm/pull/78>`_

Version 10.10
=============

* Upgrade to qiskit ~= 0.44.1. `#77 <https://github.com/iqm-finland/qiskit-on-iqm/pull/77>`
* Make the ``max_circuits`` property of ``IQMBackend`` user-configurable. `#77 <https://github.com/iqm-finland/qiskit-on-iqm/pull/77>`
* Implement ``error_message`` method for ``IQMJob``. `#77 <https://github.com/iqm-finland/qiskit-on-iqm/pull/77>``
* Explicitly specify symmetric CZ properties when building the transpilation target. `#77 <https://github.com/iqm-finland/qiskit-on-iqm/pull/77>`

Version 10.9
============

* Upgrade to iqm-client >= 13.2. `#76 <https://github.com/iqm-finland/qiskit-on-iqm/pull/76>`_

Version 10.8
============

* Fix two-qubit gate error construction in ``IQMFakeBackend``.

Version 10.7
============

* Capture execution timestamps in :meth:`IQMJob.result`.

Version 10.6
============

* More accurate mapping of job statuses in :meth:`IQMJob.status`.
* Documentation fixes.

Version 10.5
============

* Clarify the documentation on backend options. `#73 <https://github.com/iqm-finland/qiskit-on-iqm/pull/73>`_

Version 10.4
============

* Support the identity gate. `#71 <https://github.com/iqm-finland/qiskit-on-iqm/pull/71>`_

Version 10.3
============

* Add support for Python 3.11. `#70 <https://github.com/iqm-finland/qiskit-on-iqm/pull/70>`_

Version 10.2
============

* Implement ``cancel`` method for ``IQMJob``. `#69 <https://github.com/iqm-finland/qiskit-on-iqm/pull/69>`_

Version 10.1
============

* Update the script link for the Hello world example. `#68 <https://github.com/iqm-finland/qiskit-on-iqm/pull/68>`_

Version 10.0
============

* Fix a bug in the Hello world example. `#67 <https://github.com/iqm-finland/qiskit-on-iqm/pull/67>`_

Version 9.0
============
* Add readout errors to ``IQMErrorProfile``. `#50 <https://github.com/iqm-finland/qiskit-on-iqm/pull/50>`_

Version 8.3
============

* Bugfixes for ``heralding`` run with zero shots returned. `#65 <https://github.com/iqm-finland/qiskit-on-iqm/pull/65>`_
* Allow specifying ``calibration_set_id`` both as string and as ``UUID``. `#65 <https://github.com/iqm-finland/qiskit-on-iqm/pull/65>`_

Version 8.2
============

* Add ``heralding`` option to ``IQMBackend``. `#63 <https://github.com/iqm-finland/qiskit-on-iqm/pull/63>`_
* Upgrade to ``IQMClient`` version 12.5. `#63 <https://github.com/iqm-finland/qiskit-on-iqm/pull/63>`_

Version 8.1
===========

* Upgrade to IQMClient version 12.4 `#61 <https://github.com/iqm-finland/qiskit-on-iqm/pull/61>`_
* Add parameter ``circuit_duration_check`` allowing to control server-side maximum circuit duration check `#61 <https://github.com/iqm-finland/qiskit-on-iqm/pull/61>`_

Version 8.0
===========

* Update the README `#58 <https://github.com/iqm-finland/qiskit-on-iqm/pull/58>`_ and `#60 <https://github.com/iqm-finland/qiskit-on-iqm/pull/60>`_
* Clarify the example script `#62 <https://github.com/iqm-finland/qiskit-on-iqm/pull/62>`_

Version 7.15
============

* Add info about custom calibration set to user guide `#59 <https://github.com/iqm-finland/qiskit-on-iqm/pull/59>`_

Version 7.14
============

* Generate license information for dependencies on every release `#57 <https://github.com/iqm-finland/qiskit-on-iqm/pull/57>`_

Version 7.13
============

* Upgrade to IQMClient version 12.2 `#56 <https://github.com/iqm-finland/qiskit-on-iqm/pull/56>`_

Version 7.12
============

* Upgrade to IQMClient version 12.0 `#55 <https://github.com/iqm-finland/qiskit-on-iqm/pull/55>`_

Version 7.11
============

* Bump Qiskit dependency to `~= 0.42.1` `#54 <https://github.com/iqm-finland/qiskit-on-iqm/pull/54>`_

Version 7.10
============

* Add facade backend for Adonis by introducing ``facade_adonis`` backend type `#53 <https://github.com/iqm-finland/qiskit-on-iqm/pull/53>`_

Version 7.9
===========

* Add request into result metadata `#51 <https://github.com/iqm-finland/qiskit-on-iqm/pull/51>`_

Version 7.8
===========

* Drop circuit metadata if it is not JSON serializable `#49 <https://github.com/iqm-finland/qiskit-on-iqm/pull/49>`_
* Produce ``UserWarning`` if metadata is dropped `#49 <https://github.com/iqm-finland/qiskit-on-iqm/pull/49>`_

Version 7.7
===========

* "Pin down" supported Python versions to 3.9 and 3.10. `#40 <https://github.com/iqm-finland/qiskit-on-iqm/pull/40>`_
* Configure Tox to skip missing versions of Python interpreters when running tests. `#40 <https://github.com/iqm-finland/qiskit-on-iqm/pull/40>`_
* Move project metadata and configuration to ``pyproject.toml``. `#40 <https://github.com/iqm-finland/qiskit-on-iqm/pull/40>`_

Version 7.6
===========

* Check that circuit metadata is JSON serializable `#48 <https://github.com/iqm-finland/qiskit-on-iqm/pull/48>`_

Version 7.5
===========

* Adding noisy simulation by introducing ``IQMFakeAdonis`` and ``IQMFakeBackend`` `#35 <https://github.com/iqm-finland/qiskit-on-iqm/pull/35>`_

Version 7.4
===========

* Provide version information to IQMClient. `#45 <https://github.com/iqm-finland/qiskit-on-iqm/pull/45>`_

Version 7.3
===========

* Build and publish docs for older versions. `#43 <https://github.com/iqm-finland/qiskit-on-iqm/pull/43>`_

Version 7.2
===========

* Make the Hello world example even easier to follow. `#44 <https://github.com/iqm-finland/qiskit-on-iqm/pull/44>`_

Version 7.1
===========

* Add a simple example for getting started. `#41 <https://github.com/iqm-finland/qiskit-on-iqm/pull/41>`_

Version 7.0
===========

* Use new opaque UUID for ``calibration_set_id``. `#37 <https://github.com/iqm-finland/qiskit-on-iqm/pull/37>`_

Version 6.3
===========

* Construct ``IQMJob.circuit_metadata`` from data retrieved from the server, if needed. `#36 <https://github.com/iqm-finland/qiskit-on-iqm/pull/36>`_

Version 6.2
===========

* Upgrade to ``qiskit ~= 0.39.1`` and remove the life hack of adding measurement gates to the target. `#34 <https://github.com/iqm-finland/qiskit-on-iqm/pull/34>`_

Version 6.1
===========

* Add ``qubit_name_to_index`` and ``index_to_qubit_name`` methods to ``IQMBackend``. `#33 <https://github.com/iqm-finland/qiskit-on-iqm/pull/33>`_
* Fix the indexing order of qubits. `#33 <https://github.com/iqm-finland/qiskit-on-iqm/pull/33>`_

Version 6.0
===========

* Implement transpiler target for ``IQMBackend``. `#32 <https://github.com/iqm-finland/qiskit-on-iqm/pull/32>`_


Version 5.0
===========

* Remove ``settings`` option from ``IQMBackend.run``. `#28 <https://github.com/iqm-finland/qiskit-on-iqm/pull/28>`_

Version 4.6
===========

* Enable mypy support. `#27 <https://github.com/iqm-finland/qiskit-on-iqm/pull/27>`_

Version 4.5
===========

* Move calibration set ID from result's metadata to the individual results' metadata. `#25 <https://github.com/iqm-finland/qiskit-on-iqm/pull/25>`_

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
