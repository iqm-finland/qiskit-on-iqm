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

from qiskit_iqm.qiskit_to_iqm import MeasurementKey


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
