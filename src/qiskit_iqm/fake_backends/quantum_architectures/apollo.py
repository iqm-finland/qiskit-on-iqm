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

"""Apollo is IQM's 20-qubit architecture with a square-grid topology
"""

from .quantum_architecture import IQMQuantumArchitecture


class Apollo(IQMQuantumArchitecture):
    r"""IQM's twenty-qubit transmon device.
    
    The qubits are connected thus::
    
            QB20  QB17
            /  \  /  \
         QB19  QB16  QB12
         /  \  /  \  /  \
      QB18  QB15  QB11  QB7
         \  /  \  /  \  /
         QB14  QB10  QB6
         /  \  /  \  /
      QB13  QB9   QB5
         \  /  \  /  \
         QB8   QB4   QB2
            \  /  \  /
            QB3   QB1

    where the lines denote which qubit pairs can be subject to two-qubit gates.
    Each qubit can be rotated about any axis in the xy plane by an arbitrary angle.
    Apollo thus has the native RGate gate. The two-qubit gate CZ is native, as well.
    The qubits can be measured simultaneously or separately once, at the end of
    the circuit.
    """

    def __init__(self):
        super().__init__(
            number_of_qubits=20,
            topology=[
                [0, 1],
                [0, 3],
                [1, 4],
                [2, 3],
                [2, 7],
                [3, 4],
                [3, 8],
                [4, 5],
                [4, 9],
                [5, 6],
                [5, 10],
                [6, 11],
                [7, 8],
                [7, 12],
                [8, 9],
                [8, 13],
                [9, 10],
                [9, 14],
                [10, 11],
                [10, 15],
                [11, 16],
                [12, 13],
                [13, 14],
                [13, 17],
                [14, 15],
                [14, 18],
                [15, 16],
                [15, 19],
                [17, 18],
                [18, 19],
            ],
            basis_one_qubit_gates=["r"],
            basis_two_qubit_gates=["cz"],
            id_="apollo-architecture",
        )
