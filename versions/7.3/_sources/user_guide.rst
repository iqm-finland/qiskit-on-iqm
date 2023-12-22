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

1. Download the `bell_measure.py example file <https://raw.githubusercontent.com/iqm-finland/qiskit-on-iqm/main/examples/bell_measure.py>`_ (Save Page As...)
2. Install Qiskit on IQM as instructed below (feel free to skip the import statement)
3. Install Cortex CLI and log in as instructed in the `documentation <https://iqm-finland.github.io/cortex-cli/readme.html#installing-cortex-cli>`__
4. Set the environment variable as instructed by Cortex CLI after logging in
5. Run ``$ python bell_measure.py --server_url https://demo.qc.iqm.fi/cocos`` – replace the example URL with the correct one
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

If the IQM server you are connecting to requires authentication, you will also have to use
`Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_ to retrieve and automatically refresh access tokens,
then set the ``IQM_TOKENS_FILE`` environment variable to use those tokens.
See Cortex CLI's `documentation <https://iqm-finland.github.io/cortex-cli/readme.html>`__ for details.
Alternatively, authorize with the IQM_AUTH_SERVER, IQM_AUTH_USERNAME and IQM_AUTH_PASSWORD environment variables
or pass them as arguments to the constructor of :class:`.IQMProvider`, however this approach is less secure
and considered as deprecated.

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

We can also simulate the execution of the transpiled circuit before actually executing it:

.. code-block:: python

    from qiskit import Aer

    simulator = Aer.get_backend('qasm_simulator')
    job = execute(qc_transpiled, simulator, shots=1000)

    print(job.result().get_counts())

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
