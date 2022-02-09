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
from iqm_client.iqm_client import Instruction
from qiskit import QuantumCircuit
from qiskit.circuit import Measure
from qiskit.circuit.library import HGate, RGate, CZGate
from qiskit_iqm_provider.iqm_operation_mapping import map_operation, OperationNotSupportedError
import numpy as np


@pytest.fixture()
def circuit() -> QuantumCircuit:
    return QuantumCircuit(3, 3)


def test_raises_error_for_unsupported_operation(circuit):
    with pytest.raises(OperationNotSupportedError):
        map_operation(HGate(), [], [])


def test_maps_measurement_gate(circuit):
    mapped = map_operation(Measure(), circuit.qubits[1:2], circuit.clbits[1:2])
    expected = Instruction(
        name='measurement',
        qubits=['q1'],
        args={'key': 'c1'}
    )
    assert expected == mapped


@pytest.mark.parametrize('gate, expected_angle, expected_phase',
                         [(RGate(theta=np.pi, phi=0), 1 / 2, 0),
                          (RGate(theta=0, phi=np.pi), 0, 1 / 2),
                          (RGate(theta=0, phi=2 * np.pi), 0, 1),
                          (RGate(theta=2 * np.pi, phi=np.pi), 1, 1 / 2),
                          ])
def test_maps_to_phased_rx(circuit, gate, expected_angle, expected_phase):
    mapped = map_operation(gate, circuit.qubits[:1], circuit.clbits[:1])
    assert mapped.name == 'phased_rx'
    assert mapped.qubits == ['q0']
    # The unit for angle and phase is full turns
    assert mapped.args['angle_t'] == expected_angle
    assert mapped.args['phase_t'] == expected_phase


def test_maps_cz_gate(circuit):
    mapped = map_operation(CZGate(), circuit.qubits[0:2], circuit.clbits[0:2])
    expected = Instruction(
        name='cz',
        qubits=['q0', 'q1'],
        args={}
    )
    assert expected == mapped
