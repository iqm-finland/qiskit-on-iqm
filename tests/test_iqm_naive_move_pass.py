"""Testing IQM transpilation.
"""

from mockito import mock, when
import pytest
from qiskit.circuit import QuantumCircuit, Qubit
from qiskit.circuit.library import Permutation, QuantumVolume
from qiskit.quantum_info import Operator
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ApplyLayout, SetLayout

from iqm.iqm_client import IQMClient
from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_provider import IQMBackend


@pytest.fixture
def backend(ndonis_architecture):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(ndonis_architecture)
    return IQMBackend(client)


def test_transpile_to_IQM_semantically_preserving(backend):  # pylint: disable=too-many-locals
    qubit_registers = [
        backend.qubit_name_to_index(r) for r in backend.architecture.qubits if not r.startswith("COMP_R")
    ]
    n_qubits = len(qubit_registers)
    n_resonators = backend.num_qubits - n_qubits
    for i in range(1, n_qubits + 1):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile_to_IQM(circuit, backend)
        transpiled_operator = Operator(transpiled_circuit)

        # Update the original circuit to have the correct number of qubits and the correct layout
        original_with_resonator = QuantumCircuit(backend.num_qubits, 0)
        original_with_resonator.append(circuit, [qubit_registers[i.index] for i in circuit.qubits])

        def to_index(circuit: QuantumCircuit, qb: Qubit):
            if qb.register.name == "resonator":
                return qb.index
            if qb.register.name == "q":
                return qb.index + n_resonators
            return qb.index + n_resonators + circuit.num_qubits

        qubit_mapping = [
            to_index(circuit, transpiled_circuit.layout.initial_layout._p2v[i]) for i in range(backend.num_qubits)
        ]
        alt_mapping = [qubit_mapping.index(i) for i in range(backend.num_qubits)]

        pm = PassManager()
        pm.append([SetLayout(alt_mapping)])
        pm.append([ApplyLayout()])
        original_with_resonator_and_layout = pm.run(original_with_resonator)
        if transpiled_circuit.layout.final_layout is not None:
            final_layout = [
                to_index(circuit, transpiled_circuit.layout.final_layout._p2v[i]) for i in range(backend.num_qubits)
            ]
            p = Permutation(backend.num_qubits, final_layout).to_gate()
            original_with_resonator_and_layout.append(p, list(range(backend.num_qubits)))

        circuit_operator = Operator(original_with_resonator_and_layout)
        assert circuit_operator.equiv(transpiled_operator)
