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

import pytest
from iqm_client.iqm_client import SingleQubitMapping
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RGate
from qiskit_iqm.qiskit_to_iqm import InstructionNotSupportedError, serialize_circuit, serialize_qubit_mapping, qubit_to_name
import numpy as np


@pytest.fixture()
def circuit() -> QuantumCircuit:
    return QuantumCircuit(3, 3)


def test_qubit_to_name_no_explicit_register(circuit):
    for i, qubit in enumerate(circuit.qubits):
        assert qubit_to_name(qubit, circuit) == f'Qubit_{i}'


def test_qubit_to_name_uniqueness_for_multiple_registers():
    qreg1 = QuantumRegister(2)
    qreg2 = QuantumRegister(1)
    circuit = QuantumCircuit(qreg1, qreg2)
    qubit_names = set(qubit_to_name(qubit, circuit) for qubit in circuit.qubits)
    assert len(qubit_names) == len(circuit.qubits)  # assert that generated qubit names are unique


def test_serialize_qubit_mapping(circuit):
    mapping = dict(zip(circuit.qubits, ['Alice', 'Bob', 'Charlie']))
    mapping_serialized = serialize_qubit_mapping(mapping, circuit)
    assert mapping_serialized == [
        SingleQubitMapping(logical_name='Qubit_0', physical_name='Alice'),
        SingleQubitMapping(logical_name='Qubit_1', physical_name='Bob'),
        SingleQubitMapping(logical_name='Qubit_2', physical_name='Charlie')
    ]


def test_serialize_circuit_raises_error_for_unsupported_instruction(circuit):
    circuit.sx(0)
    with pytest.raises(InstructionNotSupportedError, match="Instruction sx not natively supported."):
        serialize_circuit(circuit)


@pytest.mark.parametrize('gate, expected_angle, expected_phase',
                         [(RGate(theta=np.pi, phi=0), 1 / 2, 0),
                          (RGate(theta=0, phi=np.pi), 0, 1 / 2),
                          (RGate(theta=0, phi=2 * np.pi), 0, 1),
                          (RGate(theta=2 * np.pi, phi=np.pi), 1, 1 / 2),
                          ])
def test_serialize_circuit_maps_r_gate(circuit, gate, expected_angle, expected_phase):
    circuit.append(gate, [0])
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    instr = circuit_ser.instructions[0]
    assert instr.name == 'phased_rx'
    assert instr.qubits == ['Qubit_0']
    # Serialized angles should be in full turns
    assert instr.args['angle_t'] == expected_angle
    assert instr.args['phase_t'] == expected_phase


def test_serialize_circuit_maps_cz_gate(circuit):
    circuit.cz(0, 2)
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'cz'
    assert circuit_ser.instructions[0].qubits == ['Qubit_0', 'Qubit_2']
    assert circuit_ser.instructions[0].args == {}


def test_serialize_circuit_maps_individual_measurements(circuit):
    circuit.measure(0, 2)
    circuit.measure(1, 1)
    circuit.measure(2, 0)
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'measurement'
    assert circuit_ser.instructions[0].qubits == ['Qubit_0', 'Qubit_1', 'Qubit_2']
    assert circuit_ser.instructions[0].args == {'key': 'mk'}


def test_serialize_circuit_respects_measurement_order(circuit):
    circuit.measure(1, 1)
    circuit.measure(2, 0)
    circuit.measure(0, 2)
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'measurement'
    assert circuit_ser.instructions[0].qubits == ['Qubit_1', 'Qubit_2', 'Qubit_0']
    assert circuit_ser.instructions[0].args == {'key': 'mk'}


def test_serialize_circuit_batch_measurement(circuit):
    circuit.measure([1, 0, 2], [0, 1, 2])
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'measurement'
    assert circuit_ser.instructions[0].qubits == ['Qubit_1', 'Qubit_0', 'Qubit_2']
    assert circuit_ser.instructions[0].args == {'key': 'mk'}
