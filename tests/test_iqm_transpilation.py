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

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.fake_backends.fake_aphrodite import IQMFakeAphrodite
from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb
from iqm.qiskit_iqm.iqm_move_layout import generate_initial_layout
from iqm.qiskit_iqm.iqm_transpilation import optimize_single_qubit_gates
from tests.utils import get_transpiled_circuit_json


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


def test_submitted_circuit(adonis_architecture):
    """Test that a circuit submitted via IQM backend gets transpiled into proper JSON."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)

    circuit.measure_all()

    # This transpilation seed maps virtual qubit 0 to physical qubit 2, and virtual qubit 1 to physical qubit 4
    # Other seeds will switch the mapping, and may also reorder the first prx instructions
    submitted_circuit = get_transpiled_circuit_json(circuit, adonis_architecture, seed_transpiler=123)

    instr_names = [f"{instr.name}:{','.join(instr.qubits)}" for instr in submitted_circuit.instructions]
    assert instr_names == [
        # CX phase 1: Hadamard on target qubit 1 (= QB3)
        'prx:QB3',
        # Hadamard on 0 (= QB5)
        'prx:QB5',
        # CX phase 2: CZ on 0,1 (= physical QB5, QB3)
        'cz:QB5,QB3',
        # CX phase 3: Hadamard again on target qubit 1 (= physical QB3)
        'prx:QB3',
        # Barrier before measurements
        'barrier:QB5,QB3',
        # Measurement on both qubits
        'measure:QB5',
        'measure:QB3',
    ]


@pytest.mark.parametrize('backend', [IQMFakeAdonis(), IQMFakeDeneb(), IQMFakeAphrodite()])
def test_optimize_single_qubit_gates_preserves_layout(backend):
    """Test that a circuit submitted via IQM backend gets transpiled into proper JSON."""

    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.measure_all()

    # In case the layout is not set
    qc_optimized = optimize_single_qubit_gates(transpile(qc, basis_gates=['r', 'cz']))
    assert qc_optimized.layout is None

    # In case the layout is set by the user
    initial_layout = generate_initial_layout(backend, qc)
    transpiled_circuit_alt = transpile(qc, backend=backend, initial_layout=initial_layout)
    for physical_qubit, logical_qubit in initial_layout.get_physical_bits().items():
        assert transpiled_circuit_alt.layout.initial_layout[logical_qubit] == physical_qubit

    # In case the layout is set by the transpiler
    transpiled_circuit = transpile(qc, backend=backend)
    layout = transpiled_circuit.layout
    qc_optimized = optimize_single_qubit_gates(transpiled_circuit)
    assert layout == qc_optimized.layout
