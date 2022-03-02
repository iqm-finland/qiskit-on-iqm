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

   At the moment IQM provides on-premises deployments of quantum computers only and does not have a quantum
   computing service open to the general public.

Let's consider the following quantum circuit which prepares and measures a Bell state:

.. code-block:: python

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    qc.draw()

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

    qc_decomposed.draw()

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
    to do the mapping manually. However in more complicated cases were SWAP gates need to be inserted to accomplish the
    mapping you can still use Qiskit tools to transpile the circuit against a certain coupling map and then extract
    ``qubit_mapping`` from the result.

Now that we have everything ready, we can run the circuit against the available IQM backend:

.. code-block:: python

    from qiskit_iqm import IQMProvider

    provider = IQMProvider(iqm_server_url, iqm_settings_path)
    backend = provider.get_backend()
    job = backend.run(qc_decomposed, shots=1000, qubit_mapping=qubit_mapping)

    print(job.result().get_counts())

Note that the code snippet above assumes that you have set the variables ``iqm_server_url`` and ``iqm_settings_path``.
If the IQM server you are connecting to requires authentication, you will also have to set the IQM_SERVER_USERNAME
and IQM_SERVER_API_KEY environment variables or pass them as arguments to the constructor of :class:`.IQMProvider`.


.. include:: ../CONTRIBUTING.rst
