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

# pylint: disable=no-name-in-module,import-error,too-many-arguments,unnecessary-lambda
"""Abstract representation of an IQM quantum architecture
"""

from typing import List, Union


class IQMQuantumArchitecture:
    """Class implementation to provide a abstract representation of
    the specifications of a quantum architecture, i.e., a chip family.
    """

    def __init__(
        self,
        no_qubits: int,
        topology: List[List[int]],
        basis_one_qubit_gates: List[str],
        basis_two_qubit_gates: List[str],
        id_: Union[str, None] = None,
    ):
        """Provides the specifications of a quantum architecture, i.e., a chip family.

        Args:
            no_qubits (int): number of qubits of the quantum architecture.
            topology (List[List[int]]): list of pairs of qubits that allow the implementation of two-qubit gates.
            basis_one_qubit_gates (List[str]): one-qubit gates supported by the quantum architecture.
            basis_two_qubit_gates (List[str]): two-qubit gates supported by the quantum architecture.
            id_ (str, optional): the identifier of the quantum architecture. Defaults to None.

        Example:
            IQMQuantumArchitecture(no_qubits=3,
                                   topology=[[0, 1], [1, 2]],
                                   basis_one_qubit_gates=['r'],
                                   basis_two_qubit_gates=['cz'],
                                   id_='example-architecture')
        """
        self.no_qubits = no_qubits
        self.qubits = tuple(range(no_qubits))
        self.topology = tuple(map(lambda x: tuple(x), topology))
        self.basis_gates = basis_one_qubit_gates + basis_two_qubit_gates
        self.id_ = id_
