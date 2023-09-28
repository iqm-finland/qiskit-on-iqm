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

from iqm.qiskit_iqm.iqm_transpilation import optimize_1_qb_gate_decomposition


def test_optimize_1qb_gate_decomposition_preserves_unitary():
    """Test that 1 qubit gate decomposition preserves the unitary of the circuit."""
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
    optimized_circuit = optimize_1_qb_gate_decomposition(transpiled_circuit)

    transpiled_unitary = simulator.run(transpiled_circuit).result().get_unitary(transpiled_circuit)

    optimized_unitary = simulator.run(optimized_circuit).result().get_unitary(optimized_circuit)

    # test that the two unitaries are equal up to a global phase
    np.testing.assert_almost_equal(
        2
        * (
            transpiled_unitary.data.shape[0]
            - np.abs(np.trace(np.matmul(transpiled_unitary.data.T.conj(), optimized_unitary.data)))
        ),
        0,
    )


def test_optimize_1qb_gate_decomposition_reduces_gate_count():
    """Test that 1 qubit gate decomposition optimizes the number of one qubit gates."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    transpiled_circuit = transpile(circuit, basis_gates=['r', 'cz'])
    optimized_circuit = optimize_1_qb_gate_decomposition(transpiled_circuit)

    assert len(optimized_circuit.get_instructions('r')) == 3


def test_optimize_1qb_gate_decomposition_raises_on_invalid_basis():
    """Test that optimisation pass raises error if gates other than `R_Z, C_Z` are provided."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)

    with pytest.raises(ValueError, match="Invalid operation 'h' found "):
        optimize_1_qb_gate_decomposition(circuit)
