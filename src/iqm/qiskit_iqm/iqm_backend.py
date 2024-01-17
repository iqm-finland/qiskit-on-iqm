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
"""Qiskit backend for IQM quantum computers.
"""
from __future__ import annotations

from abc import ABC
import re
from typing import Final, Optional

from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, IGate, Measure, RGate
from qiskit.providers import BackendV2
from qiskit.transpiler import Target

from iqm.iqm_client import QuantumArchitectureSpecification
from iqm.qiskit_iqm.move_gate import MoveGate
from iqm.qiskit_iqm.utils import is_directed_operation, is_multi_qubit_operation, sort_list

IQM_TO_QISKIT_GATE_NAME: Final[dict[str, str]] = {'prx': 'r', 'cz': 'cz'}


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

    def __init__(self, architecture: QuantumArchitectureSpecification, **kwargs):
        super().__init__(**kwargs)

        def get_num_or_zero(name: str) -> int:
            match = re.search(r'(\d+)', name)
            return int(match.group(1)) if match else 0

        qb_to_idx = {qb: idx for idx, qb in enumerate(sorted(architecture.qubits, key=get_num_or_zero))}
        operations = architecture.operations

        target = Target()
        # There is no dedicated direct way of setting just the qubit connectivity and the native gates to the target.
        # Such info is automatically deduced once all instruction properties are set. Currently, we do not retrieve
        # any properties from the server, and we are interested only in letting the target know what is the native gate
        # set and the connectivity of the device under use. Thus, we populate the target with None properties.
        if 'prx' in operations:
            target.add_instruction(
                RGate(Parameter('theta'), Parameter('phi')), {(qb_to_idx[qb],): None for [qb] in operations['prx']}
            )
        target.add_instruction(IGate(), {(qb_to_idx[qb],): None for qb in architecture.qubits})
        # Even though CZ is a symmetric gate, we still need to add properties for both directions. This is because
        # coupling maps in Qiskit are directed graphs and the gate symmetry is not implicitly planted there. It should
        # be explicitly supplied. This allows Qiskit to have coupling maps with non-symmetric gates like cx.
        if 'cz' in operations:
            target.add_instruction(
                CZGate(),
                {
                    (qb_to_idx[qb1], qb_to_idx[qb2]): None
                    for pair in operations['cz']
                    for qb1, qb2 in (pair, pair[::-1])
                },
            )
        if 'measure' in operations:
            target.add_instruction(Measure(), {(qb_to_idx[qb],): None for [qb] in operations['measure']})
        if 'move' in operations:
            target.add_instruction(
                MoveGate(), {(qb_to_idx[qb1], qb_to_idx[qb2]): None for [qb1, qb2] in operations['move']}
            )

        self._target = target
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}
        # Copy of the original quantum architecture that was used to construct the target. Used for validation only.
        self._quantum_architecture = architecture
        self.name = 'IQMBackend'

    @property
    def target(self) -> Target:
        return self._target

    def qubit_name_to_index(self, name: str) -> Optional[int]:
        """Given an IQM-style qubit name ('QB1', 'QB2', etc.) return the corresponding index in the register. Returns
        None is the given name does not belong to the backend."""
        return self._qb_to_idx.get(name)

    def index_to_qubit_name(self, index: int) -> Optional[str]:
        """Given an index in the backend register return the corresponding IQM-style qubit name ('QB1', 'QB2', etc.).
        Returns None if the given index does not correspond to any qubit in the backend."""
        return self._idx_to_qb.get(index)

    def validate_compatible_architecture(self, architecture: QuantumArchitectureSpecification) -> bool:
        """Given a quantum architecture specification returns true if its number of qubits, names of qubits and qubit
        connectivity matches the architecture of this backend."""
        qubits_match = set(architecture.qubits) == set(self._quantum_architecture.qubits)
        ops_match = compare_operations(architecture.operations, self._quantum_architecture.operations)

        self_connectivity = set(map(frozenset, self._quantum_architecture.qubit_connectivity))  # type: ignore
        target_connectivity = set(map(frozenset, architecture.qubit_connectivity))  # type: ignore
        connectivity_match = self_connectivity == target_connectivity

        return qubits_match and ops_match and connectivity_match


def compare_operations(ops1: dict[str, list[list[str]]], ops2: dict[str, list[list[str]]]) -> bool:
    """Compares the given operation sets defined by the quantum architecture. Returns true if they are the same."""
    if set(ops1.keys()) != set(ops2.keys()):
        return False
    for [op, c1] in ops1.items():
        c2 = ops2[op]
        if is_multi_qubit_operation(op):
            if not is_directed_operation(op):
                c1 = [sort_list(qbs) for qbs in c1]
                c2 = [sort_list(qbs) for qbs in c2]
            if sort_list(c1) != sort_list(c2):
                return False
        else:
            qs1 = {q for [q] in c1}
            qs2 = {q for [q] in c2}
            if qs1 != qs2:
                return False
    return True
