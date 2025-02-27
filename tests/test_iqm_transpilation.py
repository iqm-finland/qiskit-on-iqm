# Copyright 2022-2023 Qiskit on IQM developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Testing IQM transpilation.
"""

import math

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import BasisTranslator
from qiskit_aer import AerSimulator

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.fake_backends.fake_aphrodite import IQMFakeAphrodite
from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.iqm_move_layout import generate_initial_layout
from iqm.qiskit_iqm.iqm_transpilation import TOLERANCE, IQMOptimizeSingleQubitGates, optimize_single_qubit_gates
from iqm.qiskit_iqm.move_gate import MoveGate
from tests.utils import get_mocked_backend


def test_optimize_single_qubit_gates_preserves_unitary():
    """Test that single-qubit gate decomposition preserves the unitary of the circuit."""
    circuit = QuantumCircuit(2, 2)
    circuit.t(0)
    circuit.rx(0.4, 0)
    circuit.cx(0, 1)
    circuit.ry(0.7, 1)
    circuit.h(1)
    circuit.r(0.2, 0.8, 0)
    circuit.h(0)

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit = optimize_single_qubit_gates(transpiled_circuit, drop_final_rz=False)

    transpiled_circuit.save_unitary()
    optimized_circuit.save_unitary()
    simulator = AerSimulator(method='unitary')
    transpiled_unitary = simulator.run(transpiled_circuit).result().get_unitary(transpiled_circuit)
    optimized_unitary = simulator.run(optimized_circuit).result().get_unitary(optimized_circuit)

    np.testing.assert_almost_equal(transpiled_unitary.data, optimized_unitary.data)


def test_optimize_single_qubit_gates_drops_final_rz():
    """Test that single-qubit gate decomposition drops the final rz gate if requested and there is no measurement."""
    circuit = QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.h(1)
    circuit.cz(0, 1)
    circuit.h(1)
    circuit.measure(1, 0)

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit_dropped_rz = optimize_single_qubit_gates(transpiled_circuit)
    optimized_circuit = optimize_single_qubit_gates(transpiled_circuit, drop_final_rz=False)

    simulator = AerSimulator(method='statevector')
    shots = 100000

    transpiled_counts = simulator.run(transpiled_circuit, shots=shots).result().get_counts()
    optimized_counts = simulator.run(optimized_circuit, shots=shots).result().get_counts()
    optimized_dropped_rz_counts = simulator.run(optimized_circuit_dropped_rz, shots=shots).result().get_counts()

    for counts in [transpiled_counts, optimized_counts, optimized_dropped_rz_counts]:
        for key in counts:
            # rounding to one decimal to make stochastic failures unlikely
            # TODO should think of a better test
            counts[key] = np.round(counts[key] / shots, 1)

    assert transpiled_counts == optimized_counts == optimized_dropped_rz_counts
    assert len(optimized_circuit_dropped_rz.get_instructions('r')) == 3
    assert len(optimized_circuit.get_instructions('r')) == 5


def test_optimize_single_qubit_gates_reduces_gate_count():
    """Test that single-qubit gate decomposition optimizes the number of single-qubit gates."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit = optimize_single_qubit_gates(transpiled_circuit)

    assert len(optimized_circuit.get_instructions('r')) == 3


def test_optimize_single_qubit_gates_raises_on_invalid_basis():
    """Test that optimization pass raises error if gates other than ``RZ`` and ``CZ`` are provided."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)

    with pytest.raises(ValueError, match="Invalid operation 'h' found "):
        optimize_single_qubit_gates(circuit)


@pytest.mark.parametrize('backend', [IQMFakeAdonis(), IQMFakeDeneb(), IQMFakeAphrodite()])
def test_optimize_single_qubit_gates_preserves_layout(backend):
    """Test optimize_single_qubit_gates returns a circuit with a layout if the circuit had a layout."""

    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.measure_all()

    # In case the layout is not set
    qc_optimized = optimize_single_qubit_gates(transpile(qc, basis_gates=['r', 'cz']))
    assert qc_optimized.layout is None

    # In case the layout is set by the user
    if backend.has_resonators():
        initial_layout = generate_initial_layout(backend, qc).get_physical_bits()
    else:
        initial_layout = {
            physical_qubit: qc.qubits[logical_qubit]
            for logical_qubit, physical_qubit in enumerate(
                np.random.choice(range(backend.num_qubits), qc.num_qubits, False)
            )
        }
    transpiled_circuit_alt = transpile(qc, backend=backend, initial_layout=initial_layout)

    for physical_qubit, logical_qubit in initial_layout.items():
        assert transpiled_circuit_alt.layout.initial_layout[logical_qubit] == physical_qubit

    # In case the layout is set by the transpiler
    transpiled_circuit = transpile(qc, backend=backend)
    layout = transpiled_circuit.layout
    qc_optimized = optimize_single_qubit_gates(transpiled_circuit)
    assert layout == qc_optimized.layout


@pytest.mark.parametrize('optimization_level', list(range(4)))
def test_qiskit_native_transpiler(move_architecture, optimization_level):
    """Tests that a simple circuit is transpiled correctly using the Qiskit transpiler."""
    backend, _ = get_mocked_backend(move_architecture)
    # circuit should contain all our supported operations to make sure the transpiler can handle them
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.barrier(0, 1)
    qc.delay(10, 0, unit='ns')
    qc.reset(0)
    qc.cx(0, 1)
    qc.measure_all()
    transpiled_circuit = transpile(qc, backend=backend, optimization_level=optimization_level)
    validate_circuit(transpiled_circuit, backend)


def test_optimize_single_qubit_gates_works_on_invalid_move_sandwich():
    """Tests that the optimization pass works on a circuit with an invalid MOVE sandwich.
    In case the user is wanting to use the higher energy levels but also optimize the SQGs in the circuit."""
    qc = QuantumCircuit(2)
    qc.rz(0.5, 1)
    qc.append(MoveGate(), [1, 0])
    qc.x(1)
    qc.append(MoveGate(), [1, 0])
    basis_circuit = PassManager([BasisTranslator(SessionEquivalenceLibrary, ['r', 'cz', 'move'])]).run(qc)
    transpiled_circuit = PassManager(
        [BasisTranslator(SessionEquivalenceLibrary, ['r', 'cz', 'move']), IQMOptimizeSingleQubitGates(True, True)]
    ).run(basis_circuit)
    assert transpiled_circuit.count_ops()['r'] == 1
    assert transpiled_circuit.count_ops()['move'] == 2
    for gate in transpiled_circuit:
        if gate.operation.name == 'r':
            assert math.isclose(gate.operation.params[0], np.pi, rel_tol=TOLERANCE)
            assert math.isclose(gate.operation.params[1], 0, abs_tol=TOLERANCE)
