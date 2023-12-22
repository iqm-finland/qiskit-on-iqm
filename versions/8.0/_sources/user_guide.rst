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

1. Download the `bell_measure.py example file <https://raw.githubusercontent.com/iqm-finland/qiskit-on-iqm/28b614461cfe952fe3ce63bee222e4b48037012c/examples/bell_measure.py>`_ (Save Page As...)
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

   import qiskit_iqm


Running a quantum circuit on an IQM quantum computer
----------------------------------------------------

In this section we demonstrate the practicalities of using Qiskit on IQM on an example of constructing and executing
a simple quantum circuit on an IQM quantum computer.

Let's consider the following quantum circuit which prepares and measures a GHZ state:

.. code-block:: python

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(3, 3)
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
    meas_0: ═══════════════════╩══╬══╬═
                                  ║  ║
    meas_1: ══════════════════════╩══╬═
                                     ║
    meas_2: ═════════════════════════╩═

To execute this circuit against an IQM quantum computer you need to initialize an appropriate Qiskit backend instance
that represents the IQM quantum computer under use, and simply use Qiskit's ``execute`` function as normal:

.. code-block:: python

    from qiskit import execute
    from qiskit_iqm import IQMProvider

    provider = IQMProvider(iqm_server_url)
    backend = provider.get_backend()

    job = execute(qc, backend, shots=1000)

    print(job.result().get_counts())

Note that the code snippet above assumes that you have set the variable ``iqm_server_url``.

You can optionally set IQM backend specific settings as additional keyword arguments to the ``execute`` method (which
passes the values down to :meth:`.IQMBackend.run`). For example, an IQM server uses the best available calibration set
automatically; however, if you know an ID (UUID4) of a specific calibration set that you want to use, you can provide it
as follows:

.. code-block:: python

    job = execute(circuit, backend, shots=1000, calibration_set_id="f7d9642e-b0ca-4f2d-af2a-30195bd7a76d")

If the IQM server you are connecting to requires authentication, you will also have to use
`Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_ to retrieve and automatically refresh access tokens,
then set the ``IQM_TOKENS_FILE`` environment variable to use those tokens.
See Cortex CLI's `documentation <https://iqm-finland.github.io/cortex-cli/readme.html>`__ for details.
Alternatively, authorize with the IQM_AUTH_SERVER, IQM_AUTH_USERNAME and IQM_AUTH_PASSWORD environment variables
or pass them as arguments to the constructor of :class:`.IQMProvider`, however this approach is less secure
and considered as deprecated.

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

    Native operations of the backend: ['r', 'cz', 'measure']
    Coupling map of the backend: [[0, 2], [1, 2], [2, 3], [2, 4]]

At IQM we identify qubits by their names, e.g. 'QB1', 'QB2', etc. as demonstrated above. In Qiskit, qubits are
identified by their indices in the quantum register, as you can see from the printed coupling map above. Most of the
time you do not need to deal with IQM-style qubit names when using Qiskit, however when you need, the methods
:meth:`.IQMBackend.qubit_name_to_index` and :meth:`.IQMBackend.index_to_qubit_name` can become handy.

Now we can study how the circuit gets transpiled:


.. code-block:: python

    from qiskit.compiler import transpile

    qc_transpiled = transpile(qc, backend=backend, layout_method='sabre', optimization_level=3)

    print(qc_transpiled.draw(output='text'))

::

    global phase: π/2
                   ┌────────────┐┌────────┐                 ┌────────────┐┌────────┐ ░       ┌─┐
          q_2 -> 0 ┤ R(π/2,π/2) ├┤ R(π,0) ├─────────■───────┤ R(π/2,π/2) ├┤ R(π,0) ├─░───────┤M├
                   └────────────┘└────────┘         │       └────────────┘└────────┘ ░       └╥┘
    ancilla_0 -> 1 ─────────────────────────────────┼─────────────────────────────────────────╫─
                   ┌────────────┐┌────────┐         │                                ░ ┌─┐    ║
          q_0 -> 2 ┤ R(π/2,π/2) ├┤ R(π,0) ├─■───────■────────────────────────────────░─┤M├────╫─
                   └────────────┘└────────┘ │                                        ░ └╥┘    ║
    ancilla_1 -> 3 ─────────────────────────┼───────────────────────────────────────────╫─────╫─
                   ┌────────────┐┌────────┐ │ ┌────────────┐  ┌────────┐             ░  ║ ┌─┐ ║
          q_1 -> 4 ┤ R(π/2,π/2) ├┤ R(π,0) ├─■─┤ R(π/2,π/2) ├──┤ R(π,0) ├─────────────░──╫─┤M├─╫─
                   └────────────┘└────────┘   └────────────┘  └────────┘             ░  ║ └╥┘ ║
              c_0: ═════════════════════════════════════════════════════════════════════╬══╬══╬═
                                                                                        ║  ║  ║
              c_1: ═════════════════════════════════════════════════════════════════════╬══╬══╬═
                                                                                        ║  ║  ║
              c_2: ═════════════════════════════════════════════════════════════════════╬══╬══╬═
                                                                                        ║  ║  ║
           meas_0: ═════════════════════════════════════════════════════════════════════╩══╬══╬═
                                                                                           ║  ║
           meas_1: ════════════════════════════════════════════════════════════════════════╩══╬═
                                                                                              ║
           meas_2: ═══════════════════════════════════════════════════════════════════════════╩═


Simulating the execution of a transpiled circuit locally
--------------------------------------------------------

The execution of circuits can be simulated locally, with a noise model to mimic the real hardware as much as possible.
To this end, Qiskit on IQM provides the class  :class:`.IQMFakeBackend` that can be instantiated with properties of a
certain QPU, or subclasses of it such as :class:`.IQMFakeAdonis` that represent certain quantum architectures with
pre-populated properties and noise model.

.. code-block:: python

    from qiskit import execute, QuantumCircuit
    from qiskit_iqm import IQMFakeAdonis

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    backend = IQMFakeAdonis()
    job = execute(circuit, backend, shots=1000)
    job.result().get_counts()


Above, we use an :class:`.IQMFakeAdonis` instance to run a noisy simulation of ``circuit`` on a simulated 5-qubit Adonis
chip. If you want to customize the noise model instead of using the default one provided by :class:`.IQMFakeAdonis`, you
can create a copy of the fake Adonis instance with updated error profile:

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
    from qiskit_iqm import IQMProvider

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    provider = IQMProvider("https://demo.qc.iqm.fi/cocos/")
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

It is possible to run multiple circuits at once, as a batch. In many scenarios this is more time efficient than
running the circuits one by one. For batch execution there are some restriction that we shall keep in mind, namely all
circuits have to measure the same qubits, and all circuits will be executed for the same number of shots. For starters,
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

    circuits = [qc_transpiled.bind_parameters({theta: n}) for n in theta_range]
    job = execute(circuits, backend, shots=1000, optimization_level=0)

    print(job.result().get_counts())

Note that it is important to transpile the parameterized circuit before binding the values to ensure a consistent qubit
measurements across circuits in the batch.

.. include:: ../CONTRIBUTING.rst
