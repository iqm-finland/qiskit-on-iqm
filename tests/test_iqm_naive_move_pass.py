"""Testing IQM transpilation.
"""

from itertools import product
from typing import Iterable

import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PermutationGate, QuantumVolume
from qiskit.compiler import transpile
from qiskit.quantum_info import Operator, Statevector

from iqm.iqm_client import ExistingMoveHandlingOptions, QuantumArchitectureSpecification
from iqm.qiskit_iqm.fake_backends import IQMErrorProfile, IQMFakeAdonis, IQMFakeAphrodite, IQMFakeBackend, IQMFakeDeneb
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.iqm_naive_move_pass import transpile_to_IQM
from iqm.qiskit_iqm.iqm_transpilation import IQMReplaceGateWithUnitaryPass
from iqm.qiskit_iqm.move_gate import MOVE_GATE_UNITARY, MoveGate

from .utils import capture_submitted_circuits, get_mocked_backend


def quantum_volume_circuits(sizes: Iterable[int] = range(2, 6)):
    """Generate random quantum volume circuits for testing."""
    return [QuantumVolume(n) for n in sizes]


def ghz_circuits(sizes: Iterable[int] = range(2, 6)):
    """Generate GHZ circuits for testing."""
    circuits = []
    for n in sizes:
        qc = QuantumCircuit(n)
        qc.h(0)
        # for i in range(n - 1):
        #    qc.cx(i, i + 1)
        for i in range(1, n):
            qc.cx(0, i)
        circuits.append(qc)
    return circuits


def hypothetical_fake_device():
    """Generate a hypothetical fake device for testing.

          QB1   QB2
            |   |
           COMP_R1
            |   |
    QB3 - QB4   QB7 - QB8
            |   |
           COMP_R2
            |   |
          QB5   QB6


    """
    architecture = QuantumArchitectureSpecification(
        name="Hypothetical",
        qubits=["COMP_R1", "COMP_R2", "QB1", "QB2", "QB3", "QB4", "QB5", "QB6", "QB7", "QB8"],
        operations={
            "prx": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"], ["QB7"], ["QB8"]],
            "cz": [
                ["QB1", "COMP_R1"],
                ["QB2", "COMP_R1"],
                ["QB3", "QB4"],
                ["QB4", "COMP_R1"],
                ["QB4", "COMP_R2"],
                ["QB5", "COMP_R2"],
                ["QB6", "COMP_R2"],
                ["QB7", "COMP_R1"],
                ["QB7", "COMP_R2"],
                ["QB7", "QB8"],
            ],
            "move": [
                ["QB4", "COMP_R1"],
                ["QB4", "COMP_R2"],
                ["QB7", "COMP_R1"],
                ["QB7", "COMP_R2"],
            ],
            "measure": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"], ["QB7"], ["QB8"]],
            "barrier": [],
        },
        qubit_connectivity=[
            ["QB1", "COMP_R1"],
            ["QB2", "COMP_R1"],
            ["QB3", "QB4"],
            ["QB4", "COMP_R1"],
            ["QB4", "COMP_R2"],
            ["QB5", "COMP_R2"],
            ["QB6", "COMP_R2"],
            ["QB7", "COMP_R1"],
            ["QB7", "COMP_R2"],
            ["QB7", "QB8"],
        ],
    )
    error_profile = IQMErrorProfile(
        t1s={q: 35000.0 for q in architecture.qubits},
        t2s={q: 33000.0 for q in architecture.qubits},
        single_qubit_gate_depolarizing_error_parameters={
            "prx": {q: 0.0002 for q in architecture.qubits},
        },
        two_qubit_gate_depolarizing_error_parameters={
            gate: {(qb1, qb2): 0.0128 for qb1, qb2 in architecture.qubit_connectivity} for gate in ["cz", "move"]
        },
        single_qubit_gate_durations={"prx": 40.0},
        two_qubit_gate_durations={"cz": 120.0, "move": 96.0},
        readout_errors={q: {"0": 0.0, "1": 0.0} for q in architecture.qubits},
        name="sample-chip",
    )

    return IQMFakeBackend(architecture, error_profile, name="IQMHypotheticalTestingDevice")


def devices_to_test_on():
    fake_devices = [IQMFakeDeneb(), IQMFakeAdonis(), hypothetical_fake_device()]
    return fake_devices + [get_mocked_backend(device.architecture)[0] for device in fake_devices]


@pytest.mark.parametrize(
    ("circuit", "backend", "method"),
    list(
        product(
            quantum_volume_circuits(range(2, 9, 3)) + ghz_circuits(range(2, 7, 2)),
            devices_to_test_on(),
            ["iqm", "native_integration"],
        )
    ),
)
class TestTranspilation:
    def test_semantically_preserving(self, circuit, backend, method):
        """Test that the transpiled circuit is semantically equivalent to the original one."""
        print(backend.name)
        # Only run the test if the circuit fits the device
        if backend.num_qubits < circuit.num_qubits:
            pytest.skip("Circuit does not fit the device")
        # Use layout_method="trivial" to avoid initial qubit remapping.
        # Use fixed seed so that the test is deterministic.
        if method == "native_integration":
            # Use optimization_level=0 to enforce equivalence up to global phase.
            transpiled_circuit = transpile(circuit, backend, optimization_level=0, seed_transpiler=123)
        elif method == "qiskit":  # Debug case to check if the issues lies with the Qiskit transpiler.
            transpiled_circuit = transpile(circuit, target=backend.target, optimization_level=0, seed_transpiler=123)

        else:
            # Use remove_final_rzs=False to avoid equivalence up to global phase.
            transpiled_circuit = transpile_to_IQM(
                circuit,
                backend,
                optimization_level=0,
                remove_final_rzs=False,
                seed_transpiler=123,
            )
        # Fix the dimension of the original circuit to agree with the transpiled_circuit
        padded_circuit = QuantumCircuit(transpiled_circuit.num_qubits)
        padded_circuit.compose(circuit, range(circuit.num_qubits), inplace=True)
        circuit_operator = Operator.from_circuit(padded_circuit)
        print()
        print("After transpile", transpiled_circuit.layout)
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
        print(circuit)
        print(transpiled_circuit)
        # TODO figure out why the transpiled circuit is not always semantically equivalent to the original one when the GHZ is a ladder rather than a star.
        assert circuit_operator.equiv(transpiled_operator)

    @pytest.mark.parametrize('optimization_level', list(range(4)))
    def test_valid_result(self, circuit, backend, method, optimization_level):
        """Test that transpiled circuit has gates that are allowed by the backend"""
        # Only run the test if the circuit fits the device
        if backend.num_qubits < circuit.num_qubits:
            pytest.skip("Circuit does not fit the device")
        if method == "native":
            transpiled_circuit = transpile(circuit, backend, optimization_level=optimization_level)
        else:
            transpiled_circuit = transpile_to_IQM(circuit, backend, optimization_level=optimization_level)
        validate_circuit(transpiled_circuit, backend)

    def test_transpiled_circuit_keeps_layout(self, circuit, backend, method):
        """Test that the layout of the transpiled circuit is preserved."""
        # Only run the test if the circuit fits the device
        if backend.num_qubits < circuit.num_qubits:
            pytest.skip("Circuit does not fit the device")
        # TODO implement
        pytest.xfail("Not implemented yet")


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
    # Test both a FakeBackend and a mocked IQM backend.
    # NOTE the mocked client in the backend does not work nicely with pytest.mark.parametrize which causes a
    # requests.exceptions.ConnectionError: HTTPConnectionPool error when getting the DQA rather than returning the mock.
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


def test_transpile_empty_optimized_circuit():
    """In case the circuit is optimized to an empty circuit by the transpiler, it should not raise an error."""
    backend = IQMFakeDeneb()
    qc = QuantumCircuit(2)
    qc.append(MoveGate(), [0, 1])
    qc.append(MoveGate(), [0, 1])
    transpiled_circuit = transpile_to_IQM(qc, backend, existing_moves_handling=ExistingMoveHandlingOptions.REMOVE)
    assert len(transpiled_circuit) == 0

    transpiled_circuit = transpile(QuantumCircuit(), backend)
    assert len(transpiled_circuit) == 0
