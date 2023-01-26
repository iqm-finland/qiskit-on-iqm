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
"""Fake (i.e. simulated) backend for IQM Adonis QPU."""
from iqm_client import QuantumArchitectureSpecification

from qiskit_iqm.fake_backends.chip_sample import IQMChipSample
from qiskit_iqm.fake_backends.iqm_fake_backend import IQMFakeBackend


class IQMFakeAdonis(IQMFakeBackend):
    """
    Fake backend for simulating an IQM Adonis QPU.

    Args:
        chip_sample: Describes the characteristics of a specific chip sample.
        **kwargs: optional arguments to be passed to the parent Qiskit Backend initializer
    """

    def __init__(self, **kwargs):
        adonis_chip_sample = IQMChipSample(
            quantum_architecture=QuantumArchitectureSpecification(
                name="Adonis",
                operations=["phased_rx", "cz", "measurement", "barrier"],
                qubits=["QB1", "QB2", "QB3", "QB4", "QB5"],
                qubit_connectivity=[["QB1", "QB3"], ["QB2", "QB3"], ["QB3", "QB4"], ["QB3", "QB5"]],
            ),
            t1s={0: 27000.0, 1: 33000.0, 2: 25000.0, 3: 40000.0, 4: 25000.0},
            t2s={0: 20000.0, 1: 26000.0, 2: 23000.0, 3: 26000.0, 4: 7000.0},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0006, 1: 0.0054, 2: 0.0001, 3: 0.0, 4: 0.0005}},
            two_qubit_gate_depolarization_rates={
                "cz": {(0, 2): 0.0335, (1, 2): 0.0344, (3, 2): 0.0192, (4, 2): 0.0373}
            },
            one_qubit_gate_durations={"r": 40.0},
            two_qubit_gate_durations={"cz": 80.0},
            id_="sample-chip",
        )

        super().__init__(adonis_chip_sample, **kwargs)
