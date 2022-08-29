.. _User guide:

User guide
==========

This guide illustrates the main features of Qiskit on IQM. You are encouraged to run the demonstrated
code snippets and check the output yourself.


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

In this section we construct a simple quantum circuit and demonstrate how to execute it on an IQM quantum computer.

.. note::

   At the moment IQM does not provide a quantum computing service open to the general public.
   Please contact our `sales team <https://www.meetiqm.com/contact/>`_ to set up your access to an IQM quantum computer.


Let's consider the following quantum circuit which prepares and measures a Bell state:

.. code-block:: python

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    print(qc.draw(output='text'))

::

         ┌───┐     ┌─┐
    q_0: ┤ H ├──■──┤M├───
         └───┘┌─┴─┐└╥┘┌─┐
    q_1: ─────┤ X ├─╫─┤M├
              └───┘ ║ └╥┘
    c: 2/═══════════╩══╩═
                    0  1

First, we need to decompose it into IQM's native gate family:

.. code-block:: python

    from qiskit.compiler import transpile

    qc_decomposed = transpile(qc, basis_gates=['r', 'cz'])

    print(qc_decomposed.draw(output='text'))

::

    global phase: 3π/2
         ┌────────────┐┌────────┐                 ┌─┐
    q_0: ┤ R(π/2,π/2) ├┤ R(π,0) ├─■───────────────┤M├─────────────
         ├────────────┤├────────┤ │ ┌────────────┐└╥┘┌────────┐┌─┐
    q_1: ┤ R(π/2,π/2) ├┤ R(π,0) ├─■─┤ R(π/2,π/2) ├─╫─┤ R(π,0) ├┤M├
         └────────────┘└────────┘   └────────────┘ ║ └────────┘└╥┘
    c: 2/══════════════════════════════════════════╩════════════╩═
                                               0            1

Then, to run this circuit on an IQM quantum computer we need to figure out how to map the virtual qubits to physical ones.
Let's assume we are working with one of IQM's 5-qubit Adonis chips which have the following connectivity

::

          QB1
           |
    QB2 - QB3 - QB4
           |
          QB5

We can choose any pair of connected physical qubits and map the two virtual qubits in the circuit to them, e.g.

.. code-block:: python

    virtual_qubits = qc_decomposed.qubits
    qubit_mapping = {virtual_qubits[0]: 'QB1', virtual_qubits[1]: 'QB3'}

.. note::

    Currently, :class:`IQMBackend` does not support automatic generation of mapping from virtual qubits to physical ones
    using Qiskit transpilers, so it has to be done manually. In a simple scenario as above it is pretty straightforward
    to do the mapping manually. However in more complicated cases where SWAP gates need to be inserted to accomplish the
    mapping you can still use Qiskit tools to transpile the circuit against a certain coupling map and then extract
    ``qubit_mapping`` from the result.

Now that we have everything ready, we can run the circuit against the available IQM backend:

.. code-block:: python

    import json
    from qiskit_iqm import IQMProvider

    provider = IQMProvider(iqm_server_url)
    backend = provider.get_backend()
    with open(iqm_settings_path, 'r', encoding='utf-8') as f:
        settings = json.loads(f.read())
    job = backend.run(qc_decomposed, shots=1000, qubit_mapping=qubit_mapping, settings=settings)

    print(job.result().get_counts())

Note that the code snippet above assumes that you have set the variables ``iqm_server_url`` and ``iqm_settings_path``.
If you want to use the latest calibration set, omit ``settings`` argument from the ``backend.run`` call.
If you want to use a particular calibration set, provide a ``calibration_set_id`` integer argument. You cannot set both
``settings`` and ``calibration_set_id`` simultaneously, as IQM server rejects such requests.

If the IQM server you are connecting to requires authentication, you will also have to use
`Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_ to retrieve and automatically refresh access tokens,
then set the ``IQM_TOKENS_FILE`` environment variable to use those tokens.
See Cortex CLI's `documentation <https://iqm-finland.github.io/cortex-cli/readme.html>`_ for details.
Alternatively, authorize with the IQM_AUTH_SERVER, IQM_AUTH_USERNAME and IQM_AUTH_PASSWORD environment variables
or pass them as arguments to the constructor of :class:`.IQMProvider`, however this approach is less secure
and considered as deprecated.

It is also possible to run multiple circuits at once, as a batch. In many scenarios this is more time efficient than
running the circuits one by one. Currently, the batch running feature is meant to be used with parameterized circuits
only. A parameterized circuit can be constructed and ran with various values of the parameter(s) as follows:

.. code-block:: python

        import numpy as np
        from qiskit.circuit import Parameter

        qc = QuantumCircuit(2,2)
        theta = Parameter('theta')
        theta_range = np.linspace(0, 2*np.pi, 3)

        qc.h(0)
        qc.cx(0,1)
        qc.rz(theta, range(2))
        qc.cx(0,1)
        qc.h(0)
        qc.measure(0,0)

        qc_decomposed = transpile(qc, basis_gates=['r', 'cz'])

        circuits = [qc_decomposed.bind_parameters({theta: n})
                        for n in theta_range]

        qubit_mapping={qc_decomposed.qubits[0]: 'QB1', qc_decomposed.qubits[1]: 'QB2'}

        job = backend.run(qc_decomposed, shots=1000, qubit_mapping=qubit_mapping, settings=settings)

        print(job.result().get_counts())

Make sure to transpile the parameterized circuit before binding the values to ensure a consistent qubit mapping for
all circuits.

.. include:: ../CONTRIBUTING.rst
