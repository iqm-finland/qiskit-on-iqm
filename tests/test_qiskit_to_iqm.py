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
from qiskit.transpiler.layout import Layout

from iqm.iqm_client import Instruction
from iqm.qiskit_iqm.qiskit_to_iqm import MeasurementKey, deserialize_instructions, serialize_instructions

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


def test_serialize_instructions_can_allow_nonnative_gates():
    # Majority of the logic is tested in test_iqm_backend, here we only test the non-default behavior
    nonnative_gate = QuantumCircuit(3, name='nonnative').to_gate()
    circuit = QuantumCircuit(5)
    circuit.append(nonnative_gate, [1, 2, 4])
    circuit.measure_all()
    mapping = {i: f'QB{i + 1}' for i in range(5)}

    with pytest.raises(ValueError, match='is not natively supported. You need to transpile'):
        serialize_instructions(circuit, mapping)

    instructions = serialize_instructions(circuit, mapping, allowed_nonnative_gates={'nonnative'})
    assert instructions[0] == Instruction.model_construct(name='nonnative', qubits=('QB2', 'QB3', 'QB5'), args={})


def test_deserialize_instructions_empty():
    """Check that default input creates an empty qiskit quantum circuit."""
    circuit = deserialize_instructions([], {}, Layout())
    assert isinstance(circuit, QuantumCircuit)
    assert circuit.num_qubits == 0


def test_deserialize_instructions_without_layout():
    """Check that instructions are parsed for default layout."""
    instructions = [
        Instruction(name='prx', qubits=['QB1'], args={'phase_t': 0.0, 'angle_t': 0.0}),
        Instruction(name='cz', qubits=['QB1', 'QB2'], args={}),
        Instruction(name='move', qubits=['QB1', 'CR1'], args={}),
        Instruction(name='barrier', qubits=['QB1', 'QB2'], args={}),
        Instruction(name='measure', qubits=['QB1'], args={'key': 'm_3_2_1', 'feedback_key': 'm_3_2_1'}),
        Instruction(name='delay', qubits=['QB1'], args={'duration': 50e-9}),
        Instruction(
            name='cc_prx',
            qubits=['QB1'],
            args={'phase_t': 0.0, 'angle_t': 0.0, 'feedback_qubit': 'QB1', 'feedback_key': 'm_3_2_1'},
        ),
        Instruction(name='reset', qubits=['QB2'], args={}),
    ]
    circuit = deserialize_instructions(instructions, {'QB1': 0, 'QB2': 1, 'CR1': 2}, Layout())
    assert isinstance(circuit, QuantumCircuit)
    assert len(circuit.count_ops()) == len(instructions) - 1
    assert circuit.num_qubits == 3
    assert circuit.num_nonlocal_gates() == 2
    assert circuit.num_ancillas == 0
    assert circuit.num_clbits == 3
    assert len(circuit.cregs) == 3
    for circuit_instruction, name in zip(
        circuit.data, ['r', 'cz', 'move', 'barrier', 'measure', 'delay', 'r', 'reset']
    ):
        assert circuit_instruction.operation.name == name


def test_deserialize_instructions_roundtrip():
    """Check that native instructions are retrieved after a deserialize-serialize roundtrip."""
    instructions = [
        Instruction(name='prx', qubits=['QB1'], args={'phase_t': 0.1, 'angle_t': 0.0}),
        Instruction(name='cz', qubits=['QB1', 'QB2'], args={}),
        Instruction(name='move', qubits=['QB1', 'CR1'], args={}),
        Instruction(name='barrier', qubits=['QB1', 'QB2'], args={}),
        Instruction(name='measure', qubits=['QB1'], args={'key': 'm_3_2_1', 'feedback_key': 'm_3_2_1'}),
        Instruction(name='delay', qubits=['QB1'], args={'duration': 50e-9}),
        Instruction(
            name='cc_prx',
            qubits=['QB2'],
            args={'angle_t': 0.2, 'phase_t': 0.3, 'feedback_qubit': 'QB1', 'feedback_key': 'm_3_2_1'},
        ),
        Instruction(name='reset', qubits=['QB2'], args={}),
    ]
    circuit = deserialize_instructions(instructions, {'QB1': 0, 'QB2': 1, 'CR1': 2}, Layout())
    new_instructions = serialize_instructions(circuit, qubit_index_to_name={0: 'QB1', 1: 'QB2', 2: 'CR1'})
    assert new_instructions == instructions


def test_deserialize_instructions_unsupported_instruction():
    """Check that invalid instruction raises an error."""
    instruction = Instruction(name='cz', qubits=['QB1', 'QB2'], args={})
    instruction.name = 'cx'  # Purposely creating an instruction with an unsupported name.
    with pytest.raises(ValueError, match='Unsupported instruction cx in the circuit.'):
        deserialize_instructions([instruction], {'QB1': 0, 'QB2': 1, 'CR1': 2}, Layout())
