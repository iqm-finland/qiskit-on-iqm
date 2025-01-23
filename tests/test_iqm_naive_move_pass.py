"""Testing IQM transpilation.
"""

from itertools import product

import numpy as np
import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QuantumVolume
from qiskit.compiler import transpile
from qiskit.quantum_info import Operator

from iqm.iqm_client import ExistingMoveHandlingOptions
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_transpilation import IQMReplaceGateWithUnitaryPass
from iqm.qiskit_iqm.move_gate import MOVE_GATE_UNITARY, MoveGate

from .utils import capture_submitted_circuits, get_mocked_backend


def get_test_circuit(kind, size):
    if kind == "QuantumVolume":
        return QuantumVolume(size)
    if kind == "GHZ":
        qc = QuantumCircuit(size)
        qc.h(0)
        for i in range(size - 1):
            qc.cx(i, i + 1)
        return qc
    raise ValueError(f"Unknown circuit kind: {kind}")


@pytest.fixture()
def backend(request):
    return get_mocked_backend(request.getfixturevalue(request.param))[0]


@pytest.mark.parametrize(
    ("circuit_kind", "circuit_size", "backend", "transpile_method"),
    list(
        product(
            ["GHZ", "QuantumVolume"],
            [2, None],  # Try a small circuit and the largest possible circuit
            ["move_architecture", "adonis_architecture", "hypothetical_fake_architecture"],
            ["transpiled_to_IQM", "qiskit_integration"],  # "qiskit" can be used for debugging
        )
    ),
    indirect=["backend"],
)
class TestTranspilation:
    def transpile(self, optimization_level=0, transpile_seed=123, initial_layout=None):
        transpile_method = self.transpile_method
        if transpile_method == "qiskit_integration":
            return transpile(
                self.original_circuit,
                self.backend,
                initial_layout=initial_layout,
                optimization_level=optimization_level,
                seed_transpiler=transpile_seed,
            )
        if transpile_method == "qiskit":
            return transpile(
                self.original_circuit,
                target=self.backend.target,
                optimization_level=optimization_level,
                initial_layout=initial_layout,
                seed_transpiler=transpile_seed,
            )
        if transpile_method == "transpiled_to_IQM":
            return transpile_to_IQM(
                self.original_circuit,
                self.backend,
                optimization_level=optimization_level,
                initial_layout=initial_layout,
                remove_final_rzs=False,
                seed_transpiler=transpile_seed,
            )
        raise ValueError(f"Unknown transpile method: {transpile_method}")

    @pytest.fixture(autouse=True)
    def init_transpile(self, circuit_kind, circuit_size, backend, transpile_method):
        self.transpile_method = transpile_method
        self.backend = backend
        if circuit_size is None:
            circuit_size = self.backend.num_qubits
        if self.backend.num_qubits < circuit_size:
            pytest.skip("Circuit does not fit the device")
        self.original_circuit = get_test_circuit(circuit_kind, circuit_size)

    def test_semantically_preserving(self):
        """Test that the transpiled circuit is semantically equivalent to the original one."""
        # Fix the dimension of the original circuit to agree with the transpiled_circuit
        transpiled_circuit = self.transpile(initial_layout=list(range(self.original_circuit.num_qubits)))
        print(transpiled_circuit.layout)
        print(self.original_circuit.qregs)

        padded_circuit = QuantumCircuit(transpiled_circuit.num_qubits)
        padded_circuit.compose(self.original_circuit, range(self.original_circuit.num_qubits), inplace=True)
        circuit_operator = Operator.from_circuit(padded_circuit)
        if "move" in transpiled_circuit.count_ops():
            # Replace the move gate with the iSWAP unitary.
            transpiled_circuit_without_moves = IQMReplaceGateWithUnitaryPass("move", MOVE_GATE_UNITARY)(
                transpiled_circuit
            )
            initial_layout = transpiled_circuit.layout.initial_layout if transpiled_circuit.layout else None
            final_layout = transpiled_circuit.layout.final_layout if transpiled_circuit.layout else None
            transpiled_operator = Operator.from_circuit(
                transpiled_circuit_without_moves,
                ignore_set_layout=True,
                layout=initial_layout,
                final_layout=final_layout,
            )
        else:
            transpiled_operator = Operator.from_circuit(transpiled_circuit, ignore_set_layout=False)
        # TODO figure out why the transpiled circuit is not always semantically equivalent to the original one when the
        # GHZ is a ladder rather than a star.
        assert circuit_operator.equiv(transpiled_operator)

    @pytest.mark.parametrize("optimization_level", [0, 1, 2, 3])
    def test_valid_circuit(self, optimization_level):
        """Test that transpiled circuit has gates that are allowed by the backend"""
        if self.transpile_method == "qiskit":
            pytest.skip("Qiskit transpiler does not insert MOVE gates, so circuit is probably invalid.")
        transpiled_circuit = self.transpile(optimization_level=optimization_level)
        validate_circuit(transpiled_circuit, self.backend)

    def test_transpiled_circuit_keeps_layout(self):
        """Test that the layout of the transpiled circuit is preserved."""
        layout = [
            int(qb)
            for qb in np.random.choice(range(self.backend.num_qubits), self.original_circuit.num_qubits, replace=False)
        ]
        transpiled_circuit = self.transpile(initial_layout=layout, optimization_level=3)
        assert all(x == y for x, y in zip(transpiled_circuit.layout.initial_layout.get_physical_bits(), layout))


@pytest.mark.parametrize(
    "backend,restriction",
    [
        ("adonis_architecture", ["QB4", "QB3", "QB1"]),
        ("ndonis_architecture", ["QB5", "QB3", "QB1", "COMP_R"]),
    ],
    indirect=["backend"],
)
def test_transpiling_with_restricted_qubits(backend, restriction):
    """Test that the transpiled circuit only uses the qubits specified in the restriction."""
    n_qubits = 3
    circuit = QuantumVolume(n_qubits, seed=42)
    # Test both a FakeBackend and a mocked IQM backend.
    # NOTE the mocked client in the backend does not work nicely with pytest.mark.parametrize which causes a
    # requests.exceptions.ConnectionError: HTTPConnectionPool error when getting the DQA rather than returning the mock.
    restriction_idxs = [backend.qubit_name_to_index(qubit) for qubit in restriction]
    for restricted in [restriction, restriction_idxs]:
        transpiled_circuit = transpile_to_IQM(
            circuit,
            backend=backend,
            restrict_to_qubits=restricted,
            existing_moves_handling=ExistingMoveHandlingOptions.KEEP,
        )
        validate_circuit(transpiled_circuit, backend, qubit_mapping=dict(enumerate(restriction)))
        assert transpiled_circuit.num_qubits == len(restricted)
        if hasattr(backend, "client"):
            # Check that the run doesn"t fail.
            capture_submitted_circuits()
            backend.run(transpiled_circuit, shots=1, qubit_mapping=dict(enumerate(restriction)))


def test_transpile_empty_optimized_circuit(ndonis_architecture):
    """In case the circuit is optimized to an empty circuit by the transpiler, it should not raise an error."""
    backend = get_mocked_backend(ndonis_architecture)[0]
    qc = QuantumCircuit(2)
    qc.append(MoveGate(), [0, 1])
    qc.append(MoveGate(), [0, 1])
    transpiled_circuit = transpile_to_IQM(qc, backend, existing_moves_handling=ExistingMoveHandlingOptions.REMOVE)
    assert len(transpiled_circuit) == 0

    transpiled_circuit = transpile(QuantumCircuit(), backend)
    assert len(transpiled_circuit) == 0
