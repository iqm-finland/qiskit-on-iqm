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
#
"""
    This module shows how to create a chip sample. Copy this file and populate it with your measured values.
"""
from .. import IQMChipSample
from ..quantum_architectures import Adonis

adonis_chip_sample = IQMChipSample(
    quantum_architecture=Adonis(),  # can be Adonis() (5-qubit architecture) or Apollo() (20-qubit architecture)
    # T1 times for all qubits, index indicates the qubit number
    t1s=[50000.0, 50000.0, 50000.0, 50000.0, 50000.0],
    # T2 times for all qubits, index indicates the qubit number
    t2s=[50000.0, 50000.0, 50000.0, 50000.0, 50000.0],
    # Gate fidelities for one and two qubit gates, the key in the dictionary indicates the qubits the gate operates on
    one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.999, 2: 0.999, 3: 0.999, 4: 0.999}},
    two_qubit_gate_fidelities={"cz": {(0, 2): 0.999, (1, 2): 0.999, (3, 2): 0.999, (4, 2): 0.999}},
    # Gate fidelities for one and two qubit gates, the key in the dictionary indicates the qubits the gate operates on
    one_qubit_gate_depolarization_rates={"r": {0: 0.0001, 1: 0.0001, 2: 0.0001, 3: 0.0001, 4: 0.0001}},
    two_qubit_gate_depolarization_rates={"cz": {(0, 2): 0.001, (1, 2): 0.001, (3, 2): 0.001, (4, 2): 0.001}},
    # Gate durations
    one_qubit_gate_durations={"r": 40.0},
    two_qubit_gate_durations={"cz": 80.0},
    id_="sample-chip",
)
