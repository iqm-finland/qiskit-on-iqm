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

from iqm.iqm_client import QuantumArchitectureSpecification, is_directed_instruction, is_multi_qubit_instruction
from iqm.qiskit_iqm.move_gate import MoveGate

IQM_TO_QISKIT_GATE_NAME: Final[dict[str, str]] = {'prx': 'r', 'cz': 'cz'}


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

    architecture: QuantumArchitectureSpecification

    def __init__(self, architecture: QuantumArchitectureSpecification, **kwargs):
        super().__init__(**kwargs)
        self.architecture = architecture

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
        def _create_connections(name: str):
            """Creates the connection map of allowed loci for this instruction, mapped to None."""
            if is_multi_qubit_instruction(name):
                if is_directed_instruction(name):
                    return {(qb_to_idx[qb1], qb_to_idx[qb2]): None for [qb1, qb2] in operations[name]}
                return {
                    (qb_to_idx[qb1], qb_to_idx[qb2]): None
                    for pair in operations['cz']
                    for qb1, qb2 in (pair, pair[::-1])
                }
            return {(qb_to_idx[qb],): None for [qb] in operations[name]}

        if 'prx' in operations or 'phased_rx' in operations:
            target.add_instruction(
                RGate(Parameter('theta'), Parameter('phi')),
                _create_connections('prx' if 'prx' in operations else 'phased_rx'),
            )
        target.add_instruction(IGate(), {(qb_to_idx[qb],): None for qb in architecture.qubits})
        # Even though CZ is a symmetric gate, we still need to add properties for both directions. This is because
        # coupling maps in Qiskit are directed graphs and the gate symmetry is not implicitly planted there. It should
        # be explicitly supplied. This allows Qiskit to have coupling maps with non-symmetric gates like cx.
        if 'cz' in operations:
            target.add_instruction(CZGate(), _create_connections('cz'))
        if 'measure' in operations:
            target.add_instruction(Measure(), _create_connections('measure'))
        if 'measurement' in operations:
            target.add_instruction(Measure(), _create_connections('measurement'))
        if 'move' in operations:
            target.add_instruction(MoveGate(), _create_connections('move'))

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
        ops_match = architecture.has_equivalent_operations(self._quantum_architecture)

        self_connectivity = set(map(frozenset, self._quantum_architecture.qubit_connectivity))  # type: ignore
        target_connectivity = set(map(frozenset, architecture.qubit_connectivity))  # type: ignore
        connectivity_match = self_connectivity == target_connectivity

        return qubits_match and ops_match and connectivity_match
