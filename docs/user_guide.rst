.. _User guide:

User guide
==========

This guide illustrates the main features of Qiskit on IQM. You are encouraged to run the demonstrated
code snippets and check the output yourself.

.. note::

   At the moment IQM does not provide a quantum computing service open to the general public.
   Please contact our `sales team <https://www.meetiqm.com/contact/>`_ to set up your access to an IQM quantum
   computer.


Hello, world!
-------------

Here's the quickest and easiest way to execute a small computation on an IQM quantum computer and check that
things are set up correctly:

1. Download the `bell_measure.py example file <https://raw.githubusercontent.com/iqm-finland/qiskit-on-iqm/main/src/iqm/qiskit_iqm/examples/bell_measure.py>`_ (Save Page As...)
2. Install Qiskit on IQM as instructed below (feel free to skip the import statement)
3. Install Cortex CLI and log in as instructed in the `documentation <https://iqm-finland.github.io/cortex-cli/readme.html#installing-cortex-cli>`__
4. Set the environment variable as instructed by Cortex CLI after logging in
5. Run ``$ python bell_measure.py --cortex_server_url https://demo.qc.iqm.fi/cocos`` – replace the example URL with the correct one
6. If you're connecting to a real quantum computer, the output should show almost half of the measurements resulting in '00' and almost half in '11' – if this is the case, things are set up correctly!


Installation
------------

The recommended way is to install the distribution package ``qiskit-iqm`` directly from the
Python Package Index (PyPI):

.. code-block:: bash

   $ pip install qiskit-iqm


After installation Qiskit on IQM can be imported in your Python code as follows:

.. code-block:: python

   from iqm import qiskit_iqm


Running a quantum circuit on an IQM quantum computer
----------------------------------------------------

In this section we demonstrate the practicalities of using Qiskit on IQM on an example of constructing and executing
a simple quantum circuit on an IQM quantum computer.

Let's consider the following quantum circuit which prepares and measures a GHZ state:

.. code-block:: python

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.measure_all()

    print(qc.draw(output='text'))

::

            ┌───┐           ░ ┌─┐
       q_0: ┤ H ├──■────■───░─┤M├──────
            └───┘┌─┴─┐  │   ░ └╥┘┌─┐
       q_1: ─────┤ X ├──┼───░──╫─┤M├───
                 └───┘┌─┴─┐ ░  ║ └╥┘┌─┐
       q_2: ──────────┤ X ├─░──╫──╫─┤M├
                      └───┘ ░  ║  ║ └╥┘
    meas: 3/═══════════════════╩══╩══╩═
                               0  1  2


To execute this circuit on an IQM quantum computer you need to initialize an :class:`.IQMProvider` instance
with the IQM server URL, use it to retrieve an :class:`.IQMBackend` instance representing the
quantum computer, and use Qiskit's ``execute`` function as usual:

.. code-block:: python

    from qiskit import execute
    from iqm.qiskit_iqm import IQMProvider

    iqm_server_url = "https://demo.qc.iqm.fi/cocos/"  # Replace this with the correct URL
    provider = IQMProvider(iqm_server_url)
    backend = provider.get_backend()

    job = execute(qc, backend, shots=1000)

    print(job.result().get_counts())

You can optionally set IQM backend specific options as additional keyword arguments to the ``execute`` method (which
passes the values down to :meth:`.IQMBackend.run`). For example, if you know an ID of a specific calibration set that
you want to use, you can provide it as follows:

.. code-block:: python

    job = execute(qc, backend, shots=1000, calibration_set_id="f7d9642e-b0ca-4f2d-af2a-30195bd7a76d")


Alternatively, you can update the values of the options directly on the backend instance using the :meth:`.IQMBackend.set_options`
and then call execution methods without specifying additional keyword arguments. You can view all available options and
their current values using `backend.options`. Below table summarizes currently available options:

.. list-table::
   :widths: 25 100
   :header-rows: 1

   * - Name
     - Description
   * - `shots`
     - Type: ``int``, Example value: ``1207``.

       Number of shots.
   * - `calibration_set_id`
     - Type: ``str``, Example value ``"f7d9642e-b0ca-4f2d-af2a-30195bd7a76d"``.

       Indicates the calibration set to use. Defaults to `None`, which means the IQM server will use the best
       available calibration set automatically.
   * - `max_circuit_duration_over_t2`
     - Type: ``float``, Example value: ``1.0``.

       Set server-side circuit disqualification threshold. If any circuit in a job is estimated to take longer than the
       shortest T2 time of any qubit used in the circuit multiplied by this value, the server will reject the job.
       Setting this value to ``0.0`` will disable circuit duration check.
       The default value ``None`` means the server default value will be used.
   * - `heralding_mode`
     - Type: :class:`~iqm.iqm_client.models.HeraldingMode`, Example value: ``"zeros"``.

       Heralding mode to use during execution. The default value is "none".
   * - `circuit_callback`
     - Type: :class:`collections.abc.Callable`, Example value: ``None``.

       A function that accepts a list of :class:`qiskit.QuantumCircuit` instances and does not return anything.
       When the backend receives circuits for execution, it will call this function (if provided) and pass those
       circuits as argument. This may be useful in situations when you do not have explicit control over transpilation,
       but need some information on how it was done. This can happen, for example, when you use pre-implemented
       algorithms and experiments in Qiskit, where the implementation of the said algorithm or experiment takes care of
       delivering correctly transpiled circuits to the backend. This callback method gives you a chance to look into
       those transpiled circuits, extract any info you need. As a side effect, you can also use this callback to modify
       the transpiled circuits in-place, just before execution, however we do not recommend to use it for this purpose.


If the IQM server you are connecting to requires authentication, you will also have to use
`Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_ to retrieve and automatically refresh access tokens,
then set the :envvar:`IQM_TOKENS_FILE` environment variable, as instructed, to point to the tokens file.
See Cortex CLI's `documentation <https://iqm-finland.github.io/cortex-cli/readme.html>`__ for details.
Alternatively, you may authenticate yourself using the :envvar:`IQM_AUTH_SERVER`,
:envvar:`IQM_AUTH_USERNAME` and :envvar:`IQM_AUTH_PASSWORD` environment variables, or pass them as
arguments to :meth:`.IQMProvider.__init__`, however this approach is less secure and considered deprecated.

.. note::

   If you're using IQM Resonance, authentication is handled differently.
   Use the :envvar:`IQM_TOKEN` environment variable to provide the API Token obtained
   from the server dashboard.


The results of a job, that was executed with IQM quantum computer, contain the original request with the
qubit mapping that was used in execution. You can check this mapping once execution has finished.

.. code-block:: python

    print(job.result().request.qubit_mapping)

::

    [
      SingleQubitMapping(logical_name='0', physical_name='QB1'),
      SingleQubitMapping(logical_name='1', physical_name='QB2'),
      SingleQubitMapping(logical_name='2', physical_name='QB3')
    ]

The job result also contains metadata of the execution including timestamps of the various steps of processing the
job. The timestamps are stored in dict ``timestamps`` in the metadata. The dict contains a timestamp for starting
and ending of each step. The timestamps are stored with keys describing the point of processing where they were
stored. For example, the timestamp of starting the circuit compilation is stored with key ``compile_start``.
In the same way the other steps have their own timestamps with keys consisting of the step name and a ``_start`` or
``_end`` suffix. In addition to processing step timestamps, there are also timestamps for the job itself,
``job_start`` for when the job request was received by the server and ``job_end`` for when the job processing
was finished.

The job processing has three steps, ``compile`` where the circuits are converted to pulse schedules, ``submit``
where the pulse schedules are submitted for execution and ``execution`` where the pulse schedules are executed
and the measurement results are returned.

If the processing of the job is terminated before it is complete, for example due to an error, the timestamps of
processing steps that were not taken are not present in the dict.

The timestamps dict can be accessed as ``timestamps`` attribute of the job results.

For example:

.. code-block:: python

    print(job.result().timestamps['job_start'])
    print(job.result().timestamps['compile_start'])
    print(job.result().timestamps['execution_end'])



The ``backend`` instance we created above provides all the standard backend functionality that one expects from a
backend in Qiskit. For this example, I am connected to an IQM backend that features a 5-qubit chip with star-like
connectivity:

::

          QB1
           |
    QB2 - QB3 - QB4
           |
          QB5

Let's examine its basis gates and the coupling map through the ``backend`` instance

.. code-block:: python

    print(f'Native operations of the backend: {backend.operation_names}')
    print(f'Coupling map of the backend: {backend.coupling_map}')

::

    Native operations of the backend: ['id', 'r', 'cz', 'measure']
    Coupling map of the backend: [[0, 2], [2, 0], [1, 2], [2, 1], [2, 3], [3, 2], [2, 4], [4, 2]]

Note that for IQM backends the identiy gate ``id`` is not actually a gate that is executed on the device and is simply omitted.
At IQM we identify qubits by their names, e.g. 'QB1', 'QB2', etc. as demonstrated above. In Qiskit, qubits are
identified by their indices in the quantum register, as you can see from the printed coupling map above. Most of the
time you do not need to deal with IQM-style qubit names when using Qiskit, however when you need, the methods
:meth:`.IQMBackend.qubit_name_to_index` and :meth:`.IQMBackend.index_to_qubit_name` can become handy.

Now we can study how the circuit gets transpiled. IQM quantum computers without a resonator (e.g. Adonis or Garnet), we can use
the default Qiskit transpiler:


.. code-block:: python

    from qiskit.compiler import transpile

    qc_transpiled = transpile(qc, backend=backend, layout_method='sabre', optimization_level=3)

    print(qc_transpiled.draw(output='text', idle_wires=False))

::

    global phase: π/2
             ┌────────────┐┌────────┐                 ┌────────────┐┌────────┐ ░       ┌─┐
    q_2 -> 0 ┤ R(π/2,π/2) ├┤ R(π,0) ├─────────■───────┤ R(π/2,π/2) ├┤ R(π,0) ├─░───────┤M├
             ├────────────┤├────────┤         │       └────────────┘└────────┘ ░ ┌─┐   └╥┘
    q_0 -> 2 ┤ R(π/2,π/2) ├┤ R(π,0) ├─■───────■────────────────────────────────░─┤M├────╫─
             ├────────────┤├────────┤ │ ┌────────────┐  ┌────────┐             ░ └╥┘┌─┐ ║
    q_1 -> 3 ┤ R(π/2,π/2) ├┤ R(π,0) ├─■─┤ R(π/2,π/2) ├──┤ R(π,0) ├─────────────░──╫─┤M├─╫─
             └────────────┘└────────┘   └────────────┘  └────────┘             ░  ║ └╥┘ ║
     meas: 3/═════════════════════════════════════════════════════════════════════╩══╩══╩═
                                                                                  0  1  2


We also provide an optimization pass specific to the native IQM gate set which aims to reduce the number
of single-qubit gates. This optimization expects an already transpiled circuit. As an example, lets apply it to the above circuit:

.. code-block:: python

    from iqm.qiskit_iqm.iqm_transpilation import optimize_single_qubit_gates

    qc_optimized = optimize_single_qubit_gates(qc_transpiled)

    print(qc_optimized.draw(output='text', idle_wires=False))

::

    global phase: 3π/2
            ┌─────────────┐   ┌─────────────┐                ░    ┌─┐
       q_0: ┤ R(π/2,3π/2) ├─■─┤ R(π/2,5π/2) ├────────────────░────┤M├───
            ├─────────────┤ │ └─────────────┘                ░ ┌─┐└╥┘
       q_2: ┤ R(π/2,3π/2) ├─■────────■───────────────────────░─┤M├─╫────
            ├─────────────┤          │       ┌─────────────┐ ░ └╥┘ ║ ┌─┐
       q_3: ┤ R(π/2,3π/2) ├──────────■───────┤ R(π/2,5π/2) ├─░──╫──╫─┤M├
            └─────────────┘                  └─────────────┘ ░  ║  ║ └╥┘
    meas: 3/════════════════════════════════════════════════════╩══╩══╩═
                                                                0  1  2

Under the hood :func:`optimize_single_qubit_gates` uses :class:`IQMOptimizeSingleQubitGates` which inherits from
the Qiskit provided class :class:`TransformationPass` and can also be used directly if you want to assemble
custom transpilation procedures manually.

Using the computational resonator
---------------------------------

Because the resonator is not a real qubit, the standard Qiskit transpiler does not know how to compile for it.
Thus, we have a custom transpile method :func:`transpile_to_IQM` that can handle devices with a resonator (e.g. Deneb).

.. code-block:: python

    import os
    from qiskit import QuantumCircuit
    from iqm.qiskit_iqm import IQMProvider, transpile_to_IQM

    circuit = QuantumCircuit(5)
    circuit.h(0)
    for i in range(1, 5):
        circuit.cx(0, i)
    circuit.measure_all()

    iqm_server_url = "https://cocos.resonance.meetiqm.com/deneb"
    provider = IQMProvider(iqm_server_url)
    backend = provider.get_backend()
    transpiled_circuit = transpile_to_IQM(circuit, backend)

    print(transpiled_circuit)

::

                                                                  ┌───────┐                                                                           ┌───────┐
    Qubit(QuantumRegister(1, 'resonator'), 0) -> 0 ───────────────┤1      ├─■─────────────────■─────────────────■─────────────────■───────────────────┤1      ├────────────
                                                   ┌─────────────┐│  Move │ │                 │                 │                 │                 ░ │  Move │         ┌─┐
            Qubit(QuantumRegister(5, 'q'), 0) -> 1 ┤ R(π/2,3π/2) ├┤0      ├─┼─────────────────┼─────────────────┼─────────────────┼─────────────────░─┤0      ├─────────┤M├
                                                   ├─────────────┤└───────┘ │ ┌─────────────┐ │                 │                 │                 ░ └──┬─┬──┘         └╥┘
            Qubit(QuantumRegister(5, 'q'), 1) -> 2 ┤ R(π/2,3π/2) ├──────────■─┤ R(π/2,5π/2) ├─┼─────────────────┼─────────────────┼─────────────────░────┤M├─────────────╫─
                                                   ├─────────────┤            └─────────────┘ │ ┌─────────────┐ │                 │                 ░    └╥┘   ┌─┐       ║
            Qubit(QuantumRegister(5, 'q'), 2) -> 3 ┤ R(π/2,3π/2) ├────────────────────────────■─┤ R(π/2,5π/2) ├─┼─────────────────┼─────────────────░─────╫────┤M├───────╫─
                                                   ├─────────────┤                              └─────────────┘ │ ┌─────────────┐ │                 ░     ║    └╥┘┌─┐    ║
            Qubit(QuantumRegister(5, 'q'), 3) -> 4 ┤ R(π/2,3π/2) ├──────────────────────────────────────────────■─┤ R(π/2,5π/2) ├─┼─────────────────░─────╫─────╫─┤M├────╫─
                                                   ├─────────────┤                                                └─────────────┘ │ ┌─────────────┐ ░     ║     ║ └╥┘┌─┐ ║
            Qubit(QuantumRegister(5, 'q'), 4) -> 5 ┤ R(π/2,3π/2) ├────────────────────────────────────────────────────────────────■─┤ R(π/2,5π/2) ├─░─────╫─────╫──╫─┤M├─╫─
                                                   └─────────────┘                                                                  └─────────────┘ ░     ║     ║  ║ └╥┘ ║
      Qubit(QuantumRegister(1, 'ancilla'), 0) -> 6 ───────────────────────────────────────────────────────────────────────────────────────────────────────╫─────╫──╫──╫──╫─
                                                                                                                                                          ║     ║  ║  ║  ║
                                              c: 5/═══════════════════════════════════════════════════════════════════════════════════════════════════════╩═════╩══╩══╩══╩═
                                                                                                                                                          1     2  3  4  0


Under the hood, the IQM transpiler pretends that the resonator does not exist for the Qiskit transpiler and then uses an additional transpiler pass (:class:`IQMNaiveResonatorMoving`)
to add Move Gates between qubits and resonators as necessary. Additionally, if ``optimize_single_qubits=True``, the :class:`IQMOptimizeSingleQubitGates` is also used.
The resulting layout shows which register is the resonator, which registers were the original circuit, which registers are not used, and how they are mapped to the
registers on the target device. As you can see in the example, qubit 0 in the orginal circuit is stored in qubit register 1, then moved into the resonator
so that all CZ gates can be performed. Lastly, logical qubit 0 is moved out of the resonator so that it can be measured.

Additionally, if the IQM transpiler is used to transpile for a device that does not have a resonator, it will simply skip the :class:`IQMNaiveResonatorMoving` step
and transpile with the Qiskit transpiler and the optional :class:`IQMOptimizeSingleQubitGates` step.
It is also possible for the user to provide :meth:`transpile_to_IQM` with an ``optimization_level`` in the same manner as the Qiskit :meth:`transpile` function.


Noisy simulation of quantum circuit execution
---------------------------------------------

The execution of circuits can be simulated locally, with a noise model to mimic the real hardware as much as possible.
To this end, Qiskit on IQM provides the class  :class:`.IQMFakeBackend` that can be instantiated with properties of a
certain QPU, or subclasses of it such as :class:`.IQMFakeAdonis` that represent certain quantum architectures with
pre-populated properties and noise model.

.. code-block:: python

    from qiskit import execute, QuantumCircuit
    from iqm.qiskit_iqm import IQMFakeAdonis

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    backend = IQMFakeAdonis()
    job = execute(circuit, backend, shots=1000)
    job.result().get_counts()


Above, we use an :class:`.IQMFakeAdonis` instance to run a noisy simulation of ``circuit`` on a simulated 5-qubit Adonis chip.
The noise model includes relaxation (:math:`T_1`) and dephasing (:math:`T_2`), gate infidelities and readout errors.
If you want to customize the noise model instead of using the default one provided by :class:`.IQMFakeAdonis`, you can create
a copy of the fake Adonis instance with updated error profile:

.. code-block:: python

    error_profile = backend.error_profile
    error_profile.t1s['QB2'] = 30000.0  # Change T1 time of QB2 as example
    custom_fake_backend = backend.copy_with_error_profile(error_profile)

Running a quantum circuit on a facade backend
---------------------------------------------

Circuits can be executed against a mock environment: an IQM server that has no real quantum computer hardware.
Results from such executions are random bits. This may be useful when developing and testing software integrations.

Qiskit on IQM contains :class:`.IQMFacadeBackend`, which allows to combine the mock remote execution with a local
noisy quantum circuit simulation. This way you can both validate your integration as well as get an idea of the expected circuit execution results.

To run a circuit this way, use the `facade_adonis` backend retrieved from the provider. Note that the provider must be
initialized with the URL of a quantum computer with the equivalent architecture (i.e. names of qubits, their
connectivity, and the native gateset should match the 5-qubit Adonis architecture).

.. code-block:: python

    from qiskit import execute, QuantumCircuit
    from iqm.qiskit_iqm import IQMProvider

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    iqm_server_url = "https://demo.qc.iqm.fi/cocos/"  # Replace this with the correct URL
    provider = IQMProvider(iqm_server_url)
    backend = provider.get_backend('facade_adonis')
    job = execute(circuit, backend, shots=1000)
    job.result().get_counts()

.. note::

   When a classical register is added to the circuit, Qiskit fills it with classical bits of value 0 by default. If the
   register is not used later, and the circuit is submitted to the IQM server, the results will not contain those
   0-filled bits. To make sure the facade backend returns results in the same format as a real IQM server,
   :meth:`.IQMFacadeBackend.run` checks for the presence of unused classical registers, and fails with an error if there
   are any.

More advanced examples
----------------------

In this section we demonstrate some less simple examples of using Qiskit on IQM and its interoperability with various
tools available in Qiskit.

It is possible to submit multiple circuits to be executed, as a batch. In many cases this is more
time efficient than running the circuits one by one. Batch execution has some restrictions: all the
circuits must measure the same qubits, and be executed for the same number of shots. For starters,
let's construct two circuits preparing and measuring different Bell states:

.. code-block:: python

    qc_1 = QuantumCircuit(2)
    qc_1.h(0)
    qc_1.cx(0, 1)
    qc_1.measure_all()

    qc_2 = QuantumCircuit(2)
    qc_2.h(0)
    qc_2.x(1)
    qc_2.cx(0, 1)
    qc_2.measure_all()

Now, we can execute them together in a batch:

.. code-block:: python

    job = execute([qc_1, qc_2], backend, initial_layout=[0, 2], shots=1000)
    print(job.result().get_counts())

The batch execution functionality can be used to run a parameterized circuit for various concrete values of parameters:

.. code-block:: python

    import numpy as np
    from qiskit.circuit import Parameter

    qc = QuantumCircuit(2)
    theta = Parameter('theta')
    theta_range = np.linspace(0, 2*np.pi, 3)

    qc.h(0)
    qc.cx(0, 1)
    qc.rz(theta, [0, 1])
    qc.cx(0, 1)
    qc.h(0)
    qc.measure_all()


    qc_transpiled = transpile(qc, backend=backend, layout_method='sabre', optimization_level=3)

    circuits = [qc_transpiled.assign_parameters({theta: n}) for n in theta_range]
    job = execute(circuits, backend, shots=1000, optimization_level=0)

    print(job.result().get_counts())

Note that it is important to transpile the parameterized circuit before binding the values to ensure a consistent qubit
measurements across circuits in the batch.

.. include:: ../CONTRIBUTING.rst
