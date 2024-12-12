"""Testing IQM transpilation.
"""

import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QuantumVolume
from qiskit.compiler import transpile
from qiskit.quantum_info import Operator

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.fake_backends.fake_aphrodite import IQMFakeAphrodite
from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_transpilation import IQMReplaceGateWithUnitaryPass
from iqm.qiskit_iqm.move_gate import MOVE_GATE_UNITARY

from .utils import capture_submitted_circuits, get_mocked_backend


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


@pytest.mark.parametrize("n_qubits", list(range(2, 6)))
def test_transpile_to_IQM_valid_result(ndonis_architecture, n_qubits):
    """Test that transpiled circuit has gates that are allowed by the backend"""
    backend, _ = get_mocked_backend(ndonis_architecture)
    for i in range(2, n_qubits):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile_to_IQM(circuit, backend, optimize_single_qubits=False)
        validate_circuit(transpiled_circuit, backend)


@pytest.mark.parametrize("n_qubits", list(range(2, 6)))
def test_qiskit_transpile_valid_result(ndonis_architecture, n_qubits):
    """Test that move gate is applied only when one qubit is in zero state."""
    backend, _ = get_mocked_backend(ndonis_architecture)
    for i in range(2, n_qubits):
        circuit = QuantumVolume(i)
        transpiled_circuit = transpile(circuit, backend)
        validate_circuit(transpiled_circuit, backend)


@pytest.mark.parametrize(
    "fake_backend,restriction",
    [
        (IQMFakeAdonis(), ["QB4", "QB3", "QB1"]),
        (IQMFakeAphrodite(), ["QB18", "QB17", "QB25"]),
        (IQMFakeDeneb(), ["QB5", "QB3", "QB1", "COMP_R"]),
    ],
)
def test_transpiling_with_restricted_qubits(fake_backend, restriction):
    """Test that the transpiled circuit only uses the qubits specified in the restriction."""
    n_qubits = 3
    circuit = QuantumVolume(n_qubits, seed=42)
    for backend in [fake_backend, get_mocked_backend(fake_backend.architecture)[0]]:
        restriction_idxs = [backend.qubit_name_to_index(qubit) for qubit in restriction]
        for restricted in [restriction, restriction_idxs]:
            print("Restriction:", restricted)
            transpiled_circuit = transpile_to_IQM(circuit, backend=backend, restrict_to_qubits=restricted)
            validate_circuit(transpiled_circuit, backend, qubit_mapping=dict(enumerate(restriction)))
            assert transpiled_circuit.num_qubits == len(restricted)
            print(transpiled_circuit)
            if hasattr(backend, "client"):
                # Check that the run doesn't fail.
                capture_submitted_circuits()
                backend.run(transpiled_circuit, shots=1, qubit_mapping=dict(enumerate(restriction)))
