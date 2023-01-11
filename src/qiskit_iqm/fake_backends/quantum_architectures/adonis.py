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
    """IQM's five-qubit transmon device.

    The qubits are connected thus::
            QB1
             |
      QB2 - QB3 - QB4
             |
            QB5

    where the lines denote which qubit pairs can be subject to two-qubit gates.

    Each qubit can be rotated about any axis in the xy plane by an arbitrary angle.
    Adonis thus has the native RGate. The two-qubit gate CZ is native, as well. 
    The qubits can be measured simultaneously or separately once, at the end of
    the circuit.
    """

    def __init__(self):
        super().__init__(
            number_of_qubits=5,
            topology=[[0, 2], [1, 2], [3, 2], [4, 2]],
            basis_one_qubit_gates=["r"],
            basis_two_qubit_gates=["cz"],
            id_="adonis-architecture",
        )
