"""Testing IQM transpilation.
"""

import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QuantumVolume
from qiskit.quantum_info import Operator

from iqm.iqm_client import Circuit as IQMCircuit
from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_transpilation import IQMReplaceGateWithUnitaryPass
from iqm.qiskit_iqm.move_gate import MOVE_GATE_UNITARY
from iqm.qiskit_iqm.qiskit_to_iqm import serialize_instructions

from .utils import get_mocked_backend


@pytest.mark.parametrize("n_qubits", list(range(2, 6)))
def test_transpile_to_IQM_star_semantically_preserving(
    ndonis_architecture, n_qubits
):  # pylint: disable=too-many-locals
    backend, _client = get_mocked_backend(ndonis_architecture)
    n_backend_qubits = backend.target.num_qubits
    if n_backend_qubits >= n_qubits:
        circuit = QuantumVolume(n_qubits, n_qubits)
        # Use optimization_level=0 to avoid that the qubits get remapped.
        transpiled_circuit = transpile_to_IQM(circuit, backend, optimization_level=0, remove_final_rzs=False)
        transpiled_circuit_without_moves = IQMReplaceGateWithUnitaryPass("move", MOVE_GATE_UNITARY)(transpiled_circuit)
        print(transpiled_circuit_without_moves)
        transpiled_operator = Operator(transpiled_circuit_without_moves)
        # Update the original circuit to have the correct number of qubits and resonators.
        original_with_resonator = QuantumCircuit(transpiled_circuit.num_qubits)
        original_with_resonator.append(circuit, range(circuit.num_qubits))

        # Make it into an Operator and cheeck equivalence.
        circuit_operator = Operator(original_with_resonator)
        assert circuit_operator.equiv(transpiled_operator)


def test_allowed_gates_only(ndonis_architecture):
    """Test that transpiled circuit has gates that are allowed by the backend"""
    backend, _client = get_mocked_backend(ndonis_architecture)
    n_qubits = backend.num_qubits
    print("test allowed ops backend size", n_qubits)
    for i in range(2, n_qubits):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile_to_IQM(circuit, backend)
        iqm_circuit = IQMCircuit(
            name="Transpiling Circuit",
            instructions=serialize_instructions(transpiled_circuit, backend._idx_to_qb),
        )
        _client._validate_circuit_instructions(
            backend.architecture,
            [iqm_circuit],
        )


def test_moves_with_zero_state(ndonis_architecture):
    """Test that move gate is applied only when one qubit is in zero state."""
    backend, _client = get_mocked_backend(ndonis_architecture)
    n_qubits = backend.num_qubits
    for i in range(2, n_qubits):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile_to_IQM(circuit, backend)
        iqm_json = IQMCircuit(
            name="Transpiling Circuit",
            instructions=serialize_instructions(
                transpiled_circuit,
                {backend.qubit_name_to_index(qubit_name): qubit_name for qubit_name in backend.physical_qubits},
            ),
        )
        _client._validate_circuit_moves(backend.architecture, iqm_json)
