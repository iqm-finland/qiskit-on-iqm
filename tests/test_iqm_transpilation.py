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
from qiskit_aer import Aer

from iqm.qiskit_iqm.iqm_transpilation import optimize_single_qubit_gates


def test_optimize_single_qubit_gates_preserves_unitary():
    """Test that single-qubit gate decomposition preserves the unitary of the circuit."""
    circuit = QuantumCircuit(2, 2)
    circuit.t(0)
    circuit.rx(0.4, 0)
    circuit.cnot(0, 1)
    circuit.ry(0.7, 1)
    circuit.h(1)
    circuit.r(0.2, 0.8, 0)
    circuit.h(0)

    simulator = Aer.get_backend(name='unitary_simulator')

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit = optimize_single_qubit_gates(transpiled_circuit, drop_final_rz=False)

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

    simulator = Aer.get_backend(name='statevector_simulator')

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit_dropped_rz = optimize_single_qubit_gates(transpiled_circuit)
    optimized_circuit = optimize_single_qubit_gates(transpiled_circuit, drop_final_rz=False)

    shots = 1000
    transpiled_counts = simulator.run(transpiled_circuit, shots=shots).result().get_counts()
    optimized_counts = simulator.run(optimized_circuit, shots=shots).result().get_counts()
    optimized_dropped_rz_counts = simulator.run(optimized_circuit_dropped_rz, shots=shots).result().get_counts()

    for counts in [transpiled_counts, optimized_counts, optimized_dropped_rz_counts]:
        for key in counts:
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
    """Test that optimisation pass raises error if gates other than ``RZ`` and ``CZ`` are provided."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)

    with pytest.raises(ValueError, match="Invalid operation 'h' found "):
        optimize_single_qubit_gates(circuit)
