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
from qiskit.compiler import transpile
from qiskit.transpiler import TranspilerError

from iqm.qiskit_iqm.iqm_circuit import IQMCircuit
from iqm.qiskit_iqm.iqm_circuit_validation import validate_circuit
from iqm.qiskit_iqm.move_gate import MoveGate
from tests.utils import describe_instruction, get_mocked_backend, get_transpiled_circuit_json


def test_move_gate_trivial_layout(move_architecture):
    """Tests that a trivial 1-to-1 layout is translated correctly."""
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [6, 0])
    qc.cz(0, 3)
    qc.cz(2, 0)
    qc.append(MoveGate(), [6, 0])
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'move:QB6,COMP_R',
        'cz:COMP_R,QB4',
        'cz:QB3,COMP_R',
        'move:QB6,COMP_R',
    ]


def test_move_gate_nontrivial_layout(move_architecture):
    """
    Test whether the transpiler can find a layout for a nontrivial circuit.
    """
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [3, 4])
    qc.append(MoveGate(), [3, 4])
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'move:QB6,COMP_R',
        'move:QB6,COMP_R',
    ]


def test_mapped_move_qubit(move_architecture):
    """
    Test that other qubit indices can be used if we manually calculate a working
    initial layout using the IQMMoveLayout() layout pass.
    """
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [3, 0])
    qc.cz(0, 2)
    qc.append(MoveGate(), [3, 0])
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'move:QB6,COMP_R',
        'cz:COMP_R,QB3',
        'move:QB6,COMP_R',
    ]


def test_mapped_move_qubit_and_resonator(move_architecture):
    qc = IQMCircuit(7)
    # Now resonator is 2, move qubit 5, so need to switch 2<->0, 5<->6
    qc.cz(2, 4)
    qc.move(5, 2)
    qc.cz(2, 1)
    qc.cz(2, 0)
    qc.move(5, 2)
    qc.h(5)
    submitted_circuit = get_transpiled_circuit_json(qc, move_architecture)
    assert [describe_instruction(i) for i in submitted_circuit.instructions] == [
        'cz:COMP_R,QB5',
        'move:QB6,COMP_R',
        'cz:COMP_R,QB2',
        'cz:COMP_R,QB1',
        'move:QB6,COMP_R',
        'prx:QB6',
    ]


def test_cant_layout_two_resonators(move_architecture):
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [0, 6])
    qc.append(MoveGate(), [3, 6])
    with pytest.raises(TranspilerError):
        get_transpiled_circuit_json(qc, move_architecture)


def test_cant_layout_two_move_qubits(move_architecture):
    qc = QuantumCircuit(7)
    qc.append(MoveGate(), [0, 6])
    qc.append(MoveGate(), [0, 4])
    with pytest.raises(TranspilerError):
        get_transpiled_circuit_json(qc, move_architecture)


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
        'prx:QB5',
        'move:QB6,COMP_R',
        'cz:COMP_R,QB4',
        'cz:QB5,COMP_R',
        'barrier:COMP_R,QB2,QB3,QB4,QB5,QB1,QB6',
        'move:QB6,COMP_R',
        'measure:QB6',
        'measure:QB4',
    ]


@pytest.mark.parametrize('optimization_level', list(range(4)))
def test_qiskit_native_transpiler(move_architecture, optimization_level):
    backend, _ = get_mocked_backend(move_architecture)
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    transpiled_circuit = transpile(qc, backend=backend, optimization_level=optimization_level)
    validate_circuit(transpiled_circuit, backend)
