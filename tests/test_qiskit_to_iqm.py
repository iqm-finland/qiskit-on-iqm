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
from numbers import Number

import numpy as np
import pytest
from iqm_client.iqm_client import SingleQubitMapping
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Parameter, ParameterExpression
from qiskit.circuit.library import RGate

from qiskit_iqm.qiskit_to_iqm import (InstructionNotSupportedError,
                                      MeasurementKey, qubit_to_name,
                                      serialize_circuit,
                                      serialize_qubit_mapping)


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


def test_qubit_to_name_no_explicit_register(circuit):
    for i, qubit in enumerate(circuit.qubits):
        assert qubit_to_name(qubit, circuit) == f'qubit_{i}'


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
        SingleQubitMapping(logical_name='qubit_0', physical_name='Alice'),
        SingleQubitMapping(logical_name='qubit_1', physical_name='Bob'),
        SingleQubitMapping(logical_name='qubit_2', physical_name='Charlie')
    ]


def test_serialize_circuit_raises_error_for_unsupported_instruction(circuit):
    circuit.sx(0)
    with pytest.raises(InstructionNotSupportedError, match='Instruction sx not natively supported.'):
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
    assert instr.qubits == ['qubit_0']
    # Serialized angles should be in full turns
    assert instr.args['angle_t'] == expected_angle
    assert instr.args['phase_t'] == expected_phase


def test_serialize_handles_parameter_expressions(circuit):
    theta = Parameter('θ')
    phi = Parameter('φ')
    circuit.r(theta, phi, 0)
    circuit_bound = circuit.bind_parameters({theta: np.pi, phi: 0})

    # First make sure that circuit_bound does indeed represent parameters as ParameterExpression
    assert len(circuit_bound.data) == 1
    instruction = circuit_bound.data[0][0]
    assert all(isinstance(param, ParameterExpression) for param in instruction.params)

    # Now check that serialization correctly handles ParameterExpression
    circuit_ser = serialize_circuit(circuit_bound)
    assert len(circuit_ser.instructions) == 1
    iqm_instruction = circuit_ser.instructions[0]
    assert isinstance(iqm_instruction.args['angle_t'], Number)
    assert isinstance(iqm_instruction.args['phase_t'], Number)


def test_serialize_circuit_maps_cz_gate(circuit):
    circuit.cz(0, 2)
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'cz'
    assert circuit_ser.instructions[0].qubits == ['qubit_0', 'qubit_2']
    assert circuit_ser.instructions[0].args == {}


def test_serialize_circuit_maps_individual_measurements(circuit):
    circuit.measure(0, 0)
    circuit.measure(1, 1)
    circuit.measure(2, 2)
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 3
    for i, instruction in enumerate(circuit_ser.instructions):
        assert instruction.name == 'measurement'
        assert instruction.qubits == [f'qubit_{i}']
        assert instruction.args == {'key': f'c_3_0_{i}'}


def test_serialize_circuit_batch_measurement(circuit):
    circuit.measure([0, 1, 2], [0, 1, 2])
    circuit_ser = serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 3
    for i, instruction in enumerate(circuit_ser.instructions):
        assert instruction.name == 'measurement'
        assert instruction.qubits == [f'qubit_{i}']
        assert instruction.args == {'key': f'c_3_0_{i}'}
