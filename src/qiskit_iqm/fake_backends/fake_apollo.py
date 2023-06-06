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
"""Fake (i.e. simulated) backend for IQM Apollo QPU.
"""
from iqm_client import QuantumArchitectureSpecification

from qiskit_iqm.fake_backends.iqm_fake_backend import IQMErrorProfile, IQMFakeBackend


def IQMFakeApollo() -> IQMFakeBackend:
    """Return IQMFakeBackend instance representing IQM's Apollo architecture."""
    architecture = QuantumArchitectureSpecification(
        name="Apollo",
        operations=["phased_rx", "cz", "measurement", "barrier"],
        qubits=[
            "QB1",
            "QB2",
            "QB3",
            "QB4",
            "QB5",
            "QB6",
            "QB7",
            "QB8",
            "QB9",
            "QB10",
            "QB11",
            "QB12",
            "QB13",
            "QB14",
            "QB15",
            "QB16",
            "QB17",
            "QB18",
            "QB19",
            "QB20",
        ],
        qubit_connectivity=[
            ["QB1", "QB2"],
            ["QB1", "QB4"],
            ["QB2", "QB5"],
            ["QB3", "QB4"],
            ["QB8", "QB3"],
            ["QB4", "QB5"],
            ["QB9", "QB4"],
            ["QB5", "QB6"],
            ["QB10", "QB5"],
            ["QB6", "QB7"],
            ["QB11", "QB6"],
            ["QB12", "QB7"],
            ["QB8", "QB9"],
            ["QB8", "QB13"],
            ["QB9", "QB10"],
            ["QB9", "QB14"],
            ["QB10", "QB11"],
            ["QB10", "QB15"],
            ["QB11", "QB12"],
            ["QB16", "QB11"],
            ["QB17", "QB12"],
            ["QB13", "QB14"],
            ["QB14", "QB15"],
            ["QB18", "QB14"],
            ["QB16", "QB15"],
            ["QB19", "QB15"],
            ["QB16", "QB17"],
            ["QB16", "QB20"],
            ["QB18", "QB19"],
            ["QB19", "QB20"],
        ],
    )
    error_profile = IQMErrorProfile(  # Coherence times in nanoseconds
        t1s={
            "QB1": 27000.0,
            "QB2": 33000.0,
            "QB3": 25000.0,
            "QB4": 40000.0,
            "QB5": 25000.0,
            "QB6": 27000.0,
            "QB7": 33000.0,
            "QB8": 25000.0,
            "QB9": 40000.0,
            "QB10": 25000.0,
            "QB11": 27000.0,
            "QB12": 33000.0,
            "QB13": 25000.0,
            "QB14": 40000.0,
            "QB15": 25000.0,
            "QB16": 27000.0,
            "QB17": 33000.0,
            "QB18": 25000.0,
            "QB19": 40000.0,
            "QB20": 25000.0,
        },
        t2s={
            "QB1": 20000.0,
            "QB2": 26000.0,
            "QB3": 23000.0,
            "QB4": 26000.0,
            "QB5": 7000.0,
            "QB6": 20000.0,
            "QB7": 26000.0,
            "QB8": 23000.0,
            "QB9": 26000.0,
            "QB10": 7000.0,
            "QB11": 20000.0,
            "QB12": 26000.0,
            "QB13": 23000.0,
            "QB14": 26000.0,
            "QB15": 7000.0,
            "QB16": 20000.0,
            "QB17": 26000.0,
            "QB18": 23000.0,
            "QB19": 26000.0,
            "QB20": 7000.0,
        },
        single_qubit_gate_depolarizing_error_parameters={
            "phased_rx": {
                "QB1": 0.0006,
                "QB2": 0.0054,
                "QB3": 0.0001,
                "QB4": 0.0,
                "QB5": 0.0005,
                "QB6": 0.0006,
                "QB7": 0.0054,
                "QB8": 0.0001,
                "QB9": 0.0,
                "QB10": 0.0005,
                "QB11": 0.0006,
                "QB12": 0.0054,
                "QB13": 0.0001,
                "QB14": 0.0,
                "QB15": 0.0005,
                "QB16": 0.0006,
                "QB17": 0.0054,
                "QB18": 0.0001,
                "QB19": 0.0,
                "QB20": 0.0005,
            }
        },
        two_qubit_gate_depolarizing_error_parameters={
            "cz": {
                ("QB1", "QB2"): 0.0,
                ("QB1", "QB4"): 0.0,
                ("QB2", "QB5"): 0.0,
                ("QB3", "QB4"): 0.0,
                ("QB8", "QB3"): 0.0,
                ("QB4", "QB5"): 0.0,
                ("QB9", "QB4"): 0.0,
                ("QB5", "QB6"): 0.0,
                ("QB10", "QB5"): 0.0,
                ("QB6", "QB7"): 0.0,
                ("QB11", "QB6"): 0.0,
                ("QB12", "QB7"): 0.0,
                ("QB8", "QB9"): 0.0,
                ("QB8", "QB13"): 0.0,
                ("QB9", "QB10"): 0.0,
                ("QB9", "QB14"): 0.0,
                ("QB10", "QB11"): 0.0,
                ("QB10", "QB15"): 0.0,
                ("QB11", "QB12"): 0.0,
                ("QB16", "QB11"): 0.0,
                ("QB17", "QB12"): 0.0,
                ("QB13", "QB14"): 0.0,
                ("QB14", "QB15"): 0.0,
                ("QB18", "QB14"): 0.0,
                ("QB16", "QB15"): 0.0,
                ("QB19", "QB15"): 0.0,
                ("QB16", "QB17"): 0.0,
                ("QB16", "QB20"): 0.0,
                ("QB18", "QB19"): 0.0,
                ("QB19", "QB20"): 0.0,
            }
        },
        single_qubit_gate_durations={"phased_rx": 40.0},
        two_qubit_gate_durations={"cz": 80.0},
        id_="sample-chip",
    )

    return IQMFakeBackend(architecture, error_profile)
