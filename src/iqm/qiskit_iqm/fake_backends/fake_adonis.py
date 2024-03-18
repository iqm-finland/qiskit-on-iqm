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
"""Fake backend for IQM's 5-qubit Adonis architecture.
"""
from iqm.iqm_client import QuantumArchitectureSpecification
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMErrorProfile, IQMFakeBackend


def IQMFakeAdonis() -> IQMFakeBackend:
    """Return IQMFakeBackend instance representing IQM's Adonis architecture."""
    architecture = QuantumArchitectureSpecification(
        name="Adonis",
        operations={
            "prx": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"]],
            "cz": [["QB1", "QB3"], ["QB2", "QB3"], ["QB4", "QB3"], ["QB5", "QB3"]],
            "measure": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"]],
            "barrier": [],
        },
        qubits=["QB1", "QB2", "QB3", "QB4", "QB5"],
        qubit_connectivity=[["QB1", "QB3"], ["QB2", "QB3"], ["QB3", "QB4"], ["QB3", "QB5"]],
    )
    error_profile = IQMErrorProfile(
        t1s={"QB1": 27000.0, "QB2": 33000.0, "QB3": 25000.0, "QB4": 40000.0, "QB5": 25000.0},
        t2s={"QB1": 20000.0, "QB2": 26000.0, "QB3": 23000.0, "QB4": 26000.0, "QB5": 7000.0},
        single_qubit_gate_depolarizing_error_parameters={
            "prx": {"QB1": 0.0006, "QB2": 0.0054, "QB3": 0.0001, "QB4": 0.0, "QB5": 0.0005}
        },
        two_qubit_gate_depolarizing_error_parameters={
            "cz": {("QB1", "QB3"): 0.0335, ("QB2", "QB3"): 0.0344, ("QB3", "QB4"): 0.0192, ("QB3", "QB5"): 0.0373}
        },
        single_qubit_gate_durations={"prx": 40.0},
        two_qubit_gate_durations={"cz": 80.0},
        readout_errors={
            "QB1": {"0": 0.021, "1": 0.021},
            "QB2": {"0": 0.018, "1": 0.018},
            "QB3": {"0": 0.056, "1": 0.056},
            "QB4": {"0": 0.021, "1": 0.021},
            "QB5": {"0": 0.023, "1": 0.023},
        },
        name="sample-chip",
    )

    return IQMFakeBackend(architecture, error_profile, name="IQMFakeAdonisBackend")
