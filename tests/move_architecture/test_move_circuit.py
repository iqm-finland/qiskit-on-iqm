# Copyright 2024 Qiskit on IQM developers
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
"""Testing the new move gate
"""
import pytest
from qiskit import QuantumCircuit
from qiskit.transpiler import TranspilerError

from iqm.qiskit_iqm.iqm_circuit import IQMCircuit
from iqm.qiskit_iqm.move_gate import MoveGate
from tests.utils import describe_instruction, get_transpiled_circuit_json


def test_move_gate_trivial_layout(move_architecture):
    """Tests that a trivial 1-to-1 layout is translated correctly."""
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [6, 0])
    qc.cz(0, 3)
    qc.cz(2, 0)
    qc.append(MoveGate(), [6, 0])
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'move:6,0',
        'cz:0,3',
        'cz:2,0',
        'move:6,0',
    ]


def test_move_gate_nontrivial_layout(move_architecture):
    """
    For now only trivial layouts (1-to-1 mapping between virtual and physical qubits) are supported
    if there are qubit connections that don't have all operations specified.
    """
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [3, 0])
    with pytest.raises(TranspilerError):
        get_transpiled_circuit_json(qc, move_architecture)


def test_mapped_move_qubit(move_architecture):
    """
    Test that other qubit indices can be used if we manually calculate a working
    initial layout using the IQMMoveLayout() layout pass.
    """
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [3, 0])
    qc.cz(0, 2)
    qc.append(MoveGate(), [3, 0])
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture, create_move_layout=True)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == ['move:6,0', 'cz:0,2', 'move:6,0']


def test_mapped_move_qubit_and_resonator(move_architecture):
    qc = IQMCircuit(7)
    # Now resonator is 2, move qubit 5, so need to switch 2<->0, 5<->6
    qc.cz(2, 4)
    qc.move(5, 2)
    qc.cz(2, 1)
    qc.cz(2, 0)
    qc.move(5, 2)
    qc.h(5)
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture, create_move_layout=True)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'cz:0,4',
        'move:6,0',
        'cz:0,1',
        'cz:0,2',
        'move:6,0',
        'prx:6',
        'prx:6',
    ]


def test_cant_layout_two_resonators(move_architecture):
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [0, 6])
    qc.append(MoveGate(), [3, 6])
    with pytest.raises(TranspilerError):
        get_transpiled_circuit_json(qc, move_architecture, create_move_layout=True)


def test_cant_layout_two_move_qubits(move_architecture):
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [0, 6])
    qc.append(MoveGate(), [0, 4])
    with pytest.raises(TranspilerError):
        get_transpiled_circuit_json(qc, move_architecture, create_move_layout=True)


def test_transpiled_circuit(move_architecture):
    """
    Tests that a circuit with a move operation is transpiled correctly into JSON.
    """
    qc = IQMCircuit(7, 2)
    qc.move(6, 0)
    qc.cz(0, 3)
    qc.h(4)
    qc.cz(4, 0)
    qc.barrier()
    qc.move(6, 0)
    qc.measure(6, 0)
    qc.measure(3, 1)
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture, seed_transpiler=1, optimization_level=0)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        # h(4) is moved before the move gate
        'prx:4',
        'prx:4',
        # move(6, 0)
        'move:6,0',
        # cz(0, 3)
        'cz:0,3',
        # cz(4, 0) is optimized before h(6)
        'cz:4,0',
        # h(6)
        # barrier()
        'barrier:0,1,2,3,4,5,6',
        # move (6, 0)
        'move:6,0',
        # measurements
        'measure:6',
        'measure:3',
    ]
