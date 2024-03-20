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
"""New architecture definitions for tests.
"""

move_architecture_specification = {
    "name": "Custom arch",
    "operations": {
        "prx": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
        "cz": [["QB1", "COMP_R"], ["QB2", "COMP_R"], ["QB3", "COMP_R"], ["QB4", "COMP_R"], ["QB5", "COMP_R"]],
        "move": [["QB6", "COMP_R"]],
        "measure": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
        "barrier": [],
    },
    "qubits": ["COMP_R", "QB1", "QB2", "QB3", "QB4", "QB5", "QB6"],
    "qubit_connectivity": [
        ["QB1", "COMP_R"],
        ["QB2", "COMP_R"],
        ["QB3", "COMP_R"],
        ["QB4", "COMP_R"],
        ["QB5", "COMP_R"],
        ["QB6", "COMP_R"],
    ],
}

move_architecture_json = {"quantum_architecture": move_architecture_specification}

ndonis_architecture_specification = {
    "name": "Ndonis",
    "operations": {
        "cz": [
            ["QB1", "COMP_R"],
            ["QB2", "COMP_R"],
            ["QB3", "COMP_R"],
            ["QB4", "COMP_R"],
            ["QB5", "COMP_R"],
            ["QB6", "COMP_R"],
        ],
        "prx": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
        "move": [
            ["QB1", "COMP_R"],
            ["QB2", "COMP_R"],
            ["QB3", "COMP_R"],
            ["QB4", "COMP_R"],
            ["QB5", "COMP_R"],
            ["QB6", "COMP_R"],
        ],
        "barrier": [],
        "measure": [["QB1"], ["QB2"], ["QB3"], ["QB4"], ["QB5"], ["QB6"]],
    },
    "qubits": ["COMP_R", "QB1", "QB2", "QB3", "QB4", "QB5", "QB6"],
    "qubit_connectivity": [
        ["QB1", "COMP_R"],
        ["QB2", "COMP_R"],
        ["QB3", "COMP_R"],
        ["QB4", "COMP_R"],
        ["QB5", "COMP_R"],
        ["QB6", "COMP_R"],
    ],
}
