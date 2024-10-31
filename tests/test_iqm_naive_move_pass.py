"""Testing IQM transpilation.
"""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QuantumVolume
from qiskit.circuit.quantumcircuitdata import CircuitInstruction
from qiskit.quantum_info import Operator

from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_provider import IQMBackend

from .utils import _get_allowed_ops, _is_valid_instruction, get_mocked_backend


def test_transpile_to_IQM_star_semantically_preserving(ndonis_architecture):  # pylint: disable=too-many-locals
    backend, _client = get_mocked_backend(ndonis_architecture)
    qubit_registers = _get_qubit_registers(backend)
    n_qubits = len(qubit_registers)
    for i in range(2, n_qubits + 1):
        circuit = QuantumVolume(i, i)
        # Use optimization_level=0 to avoid that the qubits get remapped.
        transpiled_circuit = transpile_to_IQM(circuit, backend, optimization_level=0)
        transpiled_operator = Operator(transpiled_circuit)

        # Update the original circuit to have the correct number of qubits and resonators.
        original_with_resonator = QuantumCircuit(backend.num_qubits, 0)
        original_with_resonator.append(circuit, [qubit_registers[circuit.find_bit(i)[0]] for i in circuit.qubits])

        # Make it into an Operator and cheeck equivalence.
        circuit_operator = Operator(original_with_resonator)
        assert circuit_operator.equiv(transpiled_operator)


def test_allowed_gates_only(ndonis_architecture):
    """Test that transpiled circuit has gates that are allowed by the backend"""
    backend, _client = get_mocked_backend(ndonis_architecture)
    qubit_registers = _get_qubit_registers(backend)
    n_qubits = len(qubit_registers)
    allowed_ops = _get_allowed_ops(backend)
    for i in range(2, n_qubits + 1):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile_to_IQM(circuit, backend)
        for instruction in transpiled_circuit.data:
            assert _is_valid_instruction(transpiled_circuit, allowed_ops, instruction)


def test_moves_with_zero_state(ndonis_architecture):
    """Test that move gate is applied only when one qubit is in zero state."""
    backend, _client = get_mocked_backend(ndonis_architecture)
    qubit_registers = _get_qubit_registers(backend)
    n_qubits = len(qubit_registers)
    for i in range(2, n_qubits + 1):
        circuit = QuantumVolume(i)
        resonator_index = next(
            j
            for j, c in enumerate(backend.architecture.components)
            if c in backend.architecture.computational_resonators
        )
        transpiled_circuit = transpile_to_IQM(circuit, backend)
        moves = [instruction for instruction in transpiled_circuit.data if instruction.operation.name == "move"]
        assert _is_valid_move_sequence(resonator_index, moves, transpiled_circuit)


def _get_qubit_registers(backend: IQMBackend) -> list[int]:
    return [
        q
        for r in backend.architecture.components
        for q in [backend.qubit_name_to_index(r)]
        if not r in backend.architecture.computational_resonators
        if q is not None
    ]


def _is_valid_move_sequence(resonator_index: int, moves: list[CircuitInstruction], circuit: QuantumCircuit) -> bool:
    if len(moves) == 0:
        return True
    try:
        qubit_to_resonator, qubit_from_resonator, *rest = moves
        source_qubit, target_resonator = (circuit.find_bit(q)[0] for q in qubit_to_resonator.qubits)
        target_qubit, source_resonator = (circuit.find_bit(q)[0] for q in qubit_from_resonator.qubits)
        if source_qubit != target_qubit or target_resonator != resonator_index or source_resonator != resonator_index:
            return False
        return _is_valid_move_sequence(resonator_index, rest, circuit)
    except ValueError:  # mismatched number of moves
        return False
