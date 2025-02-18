"""Testing IQM transpilation.
"""

from itertools import product

import numpy as np
import pytest
import qiskit
from qiskit.circuit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QuantumVolume
from qiskit.compiler import transpile
import qiskit.passmanager
from qiskit.quantum_info import Operator
import qiskit.scheduler
import stevedore

from iqm.iqm_client import ExistingMoveHandlingOptions
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.iqm_naive_move_pass import _get_scheduling_method, transpile_to_IQM
from iqm.qiskit_iqm.iqm_transpilation import IQMReplaceGateWithUnitaryPass
from iqm.qiskit_iqm.move_gate import MOVE_GATE_UNITARY, MoveGate

from .utils import capture_submitted_circuits, get_mocked_backend


def get_test_circuit(kind, size):
    """Generates a test circuit according to the kind and size."""
    if kind == "QuantumVolume":
        return QuantumVolume(size)
    if kind == "GHZ":
        qc = QuantumCircuit(size)
        qc.h(0)
        for i in range(size - 1):
            qc.cx(i, i + 1)
        return qc
    if kind == "MCM":
        qc = QuantumCircuit(size, 2 * size)
        qc.h(0)
        for i in range(1, size):
            qc.cx(0, i)
            qc.measure(i, i)
        for i in range(size):
            qc.h(i)
            qc.measure(i, size + i)
            # Not using measure_all here because that was broken (SW-389)
        return qc
    raise ValueError(f"Unknown circuit kind: {kind}")


@pytest.fixture()
def backend(request):
    """Fixture that returns a mocked backend."""
    return get_mocked_backend(request.getfixturevalue(request.param))[0]


@pytest.mark.parametrize(
    ("circuit_kind", "circuit_size", "backend", "transpile_method"),
    list(
        product(
            ["GHZ", "QuantumVolume", "MCM"],
            [2, 5],
            ["move_architecture", "adonis_architecture", "hypothetical_fake_architecture"],
            ["transpiled_to_IQM", "qiskit_integration"],  # "qiskit" can be used for debugging
        )
    ),
    indirect=["backend"],
)
class TestTranspilation:
    """Test class for transpilation of circuits."""

    def transpile(self, optimization_level=0, transpile_seed=123, initial_layout=None):
        """Transpile the original circuit using the specified method."""
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
        """Fixture that initializes the test class with shared data to speed up testing."""
        # pylint: disable=attribute-defined-outside-init,redefined-outer-name
        self.transpile_method = transpile_method
        self.backend = backend
        self.circuit_kind = circuit_kind
        if circuit_size is None:
            circuit_size = self.backend.num_qubits
        if self.backend.num_qubits < circuit_size:
            pytest.skip("Circuit does not fit the device")
        self.original_circuit = get_test_circuit(circuit_kind, circuit_size)

    def test_semantically_preserving(self):
        """Test that the transpiled circuit is semantically equivalent to the original one."""
        # Fix the dimension of the original circuit to agree with the transpiled_circuit
        if self.circuit_kind == "MCM":
            pytest.skip("Mid circuit measurements circuits cannot be turned into an Operator.")
        transpiled_circuit = self.transpile(optimization_level=0)

        assert transpiled_circuit.num_qubits == len(transpiled_circuit.layout.initial_layout)
        assert transpiled_circuit.num_qubits == len(transpiled_circuit.layout.final_layout)

        padded_circuit = QuantumCircuit(transpiled_circuit.num_qubits)
        padded_circuit.compose(self.original_circuit, range(self.original_circuit.num_qubits), inplace=True)
        circuit_operator = Operator.from_circuit(padded_circuit)
        if "move" in transpiled_circuit.count_ops():
            # Replace the move gate with the MOVE unitary.
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


def test_transpiling_with_unused_qubits(ndonis_architecture):
    """Test that transpile_to_IQM can handle unused qubits in the circuit."""

    backend = get_mocked_backend(ndonis_architecture)[0]
    n_qubits = 3

    # multiple registers, q[1] and x[1:] are unused
    cr = QuantumRegister(1, "cr")
    q = QuantumRegister(n_qubits, "q")
    x = QuantumRegister(3, "x")
    c = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(cr, q, x, c)

    qc.rx(np.pi / 2, q[0])
    qc.append(MoveGate(), [q[0], cr[0]])
    for i in range(2, n_qubits + 1):
        if i < n_qubits:
            qubit = q[i]
        else:
            qubit = x[i - n_qubits]
        qc.rx(np.pi / 2, qubit)
        qc.cz(qubit, cr[0])
        qc.rx(-np.pi / 2, qubit)
    qc.append(MoveGate(), [q[0], cr[0]])
    qc.barrier()
    qc.measure(q, c)

    transpile_to_IQM(
        qc,
        backend=backend,
        existing_moves_handling=ExistingMoveHandlingOptions.KEEP,
    )


@pytest.mark.parametrize(
    "backend,restriction",
    [
        ("adonis_architecture", ["QB4", "QB3", "QB1"]),
        ("ndonis_architecture", ["QB5", "QB3", "QB1", "CR1"]),
    ],
    indirect=["backend"],
)
def test_transpiling_with_restricted_qubits(backend, restriction):
    """Test that the transpiled circuit only uses the qubits specified in the restriction."""
    # pylint: disable=redefined-outer-name
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
    # pylint: disable=redefined-outer-name
    backend = get_mocked_backend(ndonis_architecture)[0]
    qc = QuantumCircuit(2)
    qc.append(MoveGate(), [0, 1])
    qc.append(MoveGate(), [0, 1])
    transpiled_circuit = transpile_to_IQM(qc, backend, existing_moves_handling=ExistingMoveHandlingOptions.REMOVE)
    assert len(transpiled_circuit) == 0

    transpiled_circuit = transpile(QuantumCircuit(), backend)
    assert len(transpiled_circuit) == 0


@pytest.mark.parametrize(
    ("remove_final_rzs", "ignore_barriers", "existing_moves_handling"),
    list(
        product(
            [True, False],
            [True, False],
            [
                None,
                ExistingMoveHandlingOptions.KEEP,
                ExistingMoveHandlingOptions.REMOVE,
                ExistingMoveHandlingOptions.TRUST,
            ],
        )
    ),
)
def test_get_scheduling_method(remove_final_rzs, ignore_barriers, existing_moves_handling):
    """Test scheduling method for each input."""
    scheduling = _get_scheduling_method(False, False, remove_final_rzs, ignore_barriers, existing_moves_handling)
    assert scheduling == "default"

    scheduling = _get_scheduling_method(False, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
    assert scheduling.startswith("only_rz_optimization")

    scheduling = _get_scheduling_method(True, False, remove_final_rzs, ignore_barriers, existing_moves_handling)
    assert scheduling.startswith("only_move_routing")

    if existing_moves_handling:
        if remove_final_rzs is False:
            with pytest.raises(ValueError, match="Existing Move handling options are not compatible"):
                _get_scheduling_method(True, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
        elif remove_final_rzs and ignore_barriers:
            with pytest.raises(ValueError, match="Existing Move handling options are not compatible"):
                _get_scheduling_method(True, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
        else:
            scheduling = _get_scheduling_method(True, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
            assert scheduling.startswith("move_routing")
    else:
        if remove_final_rzs is False and ignore_barriers is True:
            with pytest.raises(ValueError, match="Move gate routing not compatible"):
                _get_scheduling_method(True, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
        else:
            scheduling = _get_scheduling_method(True, True, remove_final_rzs, ignore_barriers, existing_moves_handling)
            assert scheduling.startswith("move_routing")


@pytest.mark.parametrize(
    (
        "perform_move_routing",
        "optimize_single_qubits",
        "remove_final_rzs",
        "ignore_barriers",
        "existing_moves_handling",
    ),
    list(
        product(
            [True, False],
            [True, False],
            [True, False],
            [True, False],
            [
                None,
                ExistingMoveHandlingOptions.KEEP,
                ExistingMoveHandlingOptions.REMOVE,
                ExistingMoveHandlingOptions.TRUST,
            ],
        )
    ),
)
# pylint: disable=too-many-arguments
def test_transpile_to_IQM_flags(
    ndonis_architecture,
    perform_move_routing,
    optimize_single_qubits,
    remove_final_rzs,
    ignore_barriers,
    existing_moves_handling,
):
    if existing_moves_handling and remove_final_rzs is False and perform_move_routing and optimize_single_qubits:
        with pytest.raises(ValueError, match="Existing Move handling options are not compatible"):
            transpile_to_IQM(
                QuantumCircuit(),
                backend=get_mocked_backend(ndonis_architecture)[0],
                target=None,
                perform_move_routing=perform_move_routing,
                optimize_single_qubits=optimize_single_qubits,
                remove_final_rzs=remove_final_rzs,
                ignore_barriers=ignore_barriers,
                existing_moves_handling=existing_moves_handling,
            )
    elif (
        existing_moves_handling
        and remove_final_rzs
        and ignore_barriers
        and perform_move_routing
        and optimize_single_qubits
    ):
        with pytest.raises(ValueError, match="Existing Move handling options are not compatible"):
            transpile_to_IQM(
                QuantumCircuit(),
                backend=get_mocked_backend(ndonis_architecture)[0],
                target=None,
                perform_move_routing=perform_move_routing,
                optimize_single_qubits=optimize_single_qubits,
                remove_final_rzs=remove_final_rzs,
                ignore_barriers=ignore_barriers,
                existing_moves_handling=existing_moves_handling,
            )
    elif (
        existing_moves_handling is None
        and not remove_final_rzs
        and ignore_barriers
        and perform_move_routing
        and optimize_single_qubits
    ):
        with pytest.raises(ValueError, match="Move gate routing not compatible"):
            transpile_to_IQM(
                QuantumCircuit(),
                backend=get_mocked_backend(ndonis_architecture)[0],
                target=None,
                perform_move_routing=perform_move_routing,
                optimize_single_qubits=optimize_single_qubits,
                remove_final_rzs=remove_final_rzs,
                ignore_barriers=ignore_barriers,
                existing_moves_handling=existing_moves_handling,
            )
    else:
        schedule_method = _get_scheduling_method(
            perform_move_routing=perform_move_routing,
            optimize_single_qubits=optimize_single_qubits,
            remove_final_rzs=remove_final_rzs,
            ignore_barriers=ignore_barriers,
            existing_moves_handling=existing_moves_handling,
        )

        plugin = stevedore.ExtensionManager(
            "qiskit.transpiler.scheduling", invoke_on_load=True, propagate_map_exceptions=True
        )[schedule_method].obj

        if perform_move_routing is False and optimize_single_qubits is False:
            assert isinstance(
                plugin, qiskit.transpiler.preset_passmanagers.builtin_plugins.DefaultSchedulingPassManager
            )
        # elif perform_move_routing is False:
        else:
            assert plugin.move_gate_routing == perform_move_routing
            assert plugin.optimize_sqg == optimize_single_qubits
            if plugin.optimize_sqg:
                assert plugin.drop_final_rz == remove_final_rzs
                assert plugin.ignore_barriers == ignore_barriers

        circuit = transpile_to_IQM(
            QuantumCircuit(),
            backend=get_mocked_backend(ndonis_architecture)[0],
            target=None,
            perform_move_routing=perform_move_routing,
            optimize_single_qubits=optimize_single_qubits,
            remove_final_rzs=remove_final_rzs,
            ignore_barriers=ignore_barriers,
            existing_moves_handling=existing_moves_handling,
        )
        assert isinstance(circuit, QuantumCircuit)
