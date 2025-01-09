# Copyright 2022 Qiskit on IQM developers
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

"""Testing Qiskit to IQM conversion tools.
"""
import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from iqm.qiskit_iqm.qiskit_to_iqm import MeasurementKey
from .utils import get_transpiled_circuit_json


@pytest.fixture()
def circuit() -> QuantumCircuit:
    return QuantumCircuit(3, 3)


def test_measurement_key_to_str():
    mk = MeasurementKey('abc', 1, 2, 3)
    assert str(mk) == 'abc_1_2_3'


def test_measurement_key_from_clbit():
    qreg = QuantumRegister(3)
    creg1, creg2 = ClassicalRegister(2, name='cr1'), ClassicalRegister(1, name='cr2')

    circuit = QuantumCircuit(qreg, creg1, creg2)
    mk1 = MeasurementKey.from_clbit(creg1[0], circuit)
    mk2 = MeasurementKey.from_clbit(creg1[1], circuit)
    mk3 = MeasurementKey.from_clbit(creg2[0], circuit)
    assert str(mk1) == 'cr1_2_0_0'
    assert str(mk2) == 'cr1_2_0_1'
    assert str(mk3) == 'cr2_1_1_0'


@pytest.mark.parametrize('key_str', ['abc_4_5_6', 'a_bc_4_5_6'])
def test_measurement_key_from_string(key_str):
    mk = MeasurementKey.from_string(key_str)
    assert str(mk) == key_str


def test_circuit_to_iqm_json(adonis_architecture):
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
