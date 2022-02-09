.. _User guide:

User guide
==========

This guide illustrates the main features of Qiskit on IQM. You are encouraged to run the demonstrated
code snippets and check the output yourself.


Installation
------------

The recommended way is to install the distribution package ``qiskit-iqm-provider`` directly from the
Python Package Index (PyPI):

.. code-block:: bash

   $ pip install qiskit-iqm-provider


After installation Qiskit on IQM can be imported in your Python code as follows:

.. code-block:: python

   import qiskit_iqm_provider


Running a quantum circuit on an IQM quantum computer
----------------------------------------------------

Let us construct a simple quantum circuit, and demonstrate how it can be executed on an IQM quantum computer.

.. note::

   At the moment IQM provides on-premises deployments of their quantum computers only and does not have a quantum
   computing service open to the general public.

A quantum circuit to prepare and measure a Bell state

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

Decompose the circuit into IQM's native gate family

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

Run against IQM (TODO: this is a sketch code for now)

.. code-block:: python

    from qiskit import execute
    from qiskit_iqm_provider import IQMBackend

    backend = IQMBackend(iqm_server_url, iqm_settings)
    execute(qc_decomposed, backend)
