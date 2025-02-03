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
"""Fake backend for IQM's 6-qubit Deneb architecture.
"""
from iqm.iqm_client import QuantumArchitectureSpecification
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMErrorProfile, IQMFakeBackend


def IQMFakeDeneb() -> IQMFakeBackend:
    """Return IQMFakeBackend instance representing IQM's Deneb architecture."""

    architecture = QuantumArchitectureSpecification(
        name="Deneb",
        operations={
            "prx": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
            "cz": [
                ["QB1", "CR1"],
                ["QB2", "CR1"],
                ["QB3", "CR1"],
                ["QB4", "CR1"],
                ["QB5", "CR1"],
                ["QB6", "CR1"],
            ],
            "move": [
                ["QB1", "CR1"],
                ["QB2", "CR1"],
                ["QB3", "CR1"],
                ["QB4", "CR1"],
                ["QB5", "CR1"],
                ["QB6", "CR1"],
            ],
            "measure": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
            "barrier": [],
        },
        qubits=["CR1", "QB1", "QB2", "QB3", "QB4", "QB5", "QB6"],
        qubit_connectivity=[
            ["QB1", "CR1"],
            ["QB2", "CR1"],
            ["QB3", "CR1"],
            ["QB4", "CR1"],
            ["QB5", "CR1"],
            ["QB6", "CR1"],
        ],
    )
    error_profile = IQMErrorProfile(
        t1s={
            "CR1": 5400.0,
            "QB1": 35000.0,
            "QB2": 35000.0,
            "QB3": 35000.0,
            "QB4": 35000.0,
            "QB5": 35000.0,
            "QB6": 35000.0,
        },
        t2s={
            "CR1": 10800.0,
            "QB1": 33000.0,
            "QB2": 33000.0,
            "QB3": 33000.0,
            "QB4": 33000.0,
            "QB5": 33000.0,
            "QB6": 33000.0,
        },
        single_qubit_gate_depolarizing_error_parameters={
            "prx": {
                "CR1": 0.0,
                "QB1": 0.0002,
                "QB2": 0.0002,
                "QB3": 0.0002,
                "QB4": 0.0002,
                "QB5": 0.0002,
                "QB6": 0.0002,
            }
        },
        two_qubit_gate_depolarizing_error_parameters={
            "cz": {
                ("QB1", "CR1"): 0.0128,
                ("QB2", "CR1"): 0.0128,
                ("QB3", "CR1"): 0.0128,
                ("QB4", "CR1"): 0.0128,
                ("QB5", "CR1"): 0.0128,
                ("QB6", "CR1"): 0.0128,
            },
            "move": {
                ("QB1", "CR1"): 0.0,
                ("QB2", "CR1"): 0.0,
                ("QB3", "CR1"): 0.0,
                ("QB4", "CR1"): 0.0,
                ("QB5", "CR1"): 0.0,
                ("QB6", "CR1"): 0.0,
            },
        },
        single_qubit_gate_durations={"prx": 40.0},
        two_qubit_gate_durations={"cz": 120.0, "move": 96.0},
        readout_errors={
            "CR1": {"0": 0.0, "1": 0.0},
            "QB1": {"0": 0.02, "1": 0.02},
            "QB2": {"0": 0.02, "1": 0.02},
            "QB3": {"0": 0.02, "1": 0.02},
            "QB4": {"0": 0.02, "1": 0.02},
            "QB5": {"0": 0.02, "1": 0.02},
            "QB6": {"0": 0.02, "1": 0.02},
        },
        name="sample-chip",
    )

    return IQMFakeBackend(architecture, error_profile, name="IQMFakeDenebBackend")
