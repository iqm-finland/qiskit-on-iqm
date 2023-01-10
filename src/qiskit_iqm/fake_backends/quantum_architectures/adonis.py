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

"""Adonis is IQM's 5-qubit architecture with star topology: the central qubit is connected to the other four
"""

from .quantum_architecture import IQMQuantumArchitecture


class Adonis(IQMQuantumArchitecture):
    """Class implementation for IQMs 5-qubit QPU architecture."""

    def __init__(self):
        super().__init__(
            no_qubits=5,
            topology=[[0, 2], [1, 2], [3, 2], [4, 2]],
            basis_one_qubit_gates=["r"],
            basis_two_qubit_gates=["cz"],
            id_="adonis-architecture",
        )
