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
import itertools
import re
from typing import Final, Optional

from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, IGate, Measure, RGate
from qiskit.providers import BackendV2
from qiskit.transpiler import InstructionProperties, Target

from iqm.iqm_client import QuantumArchitectureSpecification
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

        # Construct the Qiskit instruction properties from the quantum architecture.
        target = Target()

        def _create_properties(
            op_name: str, symmetric: bool = False
        ) -> dict[tuple[int, ...], InstructionProperties | None]:
            """Creates the Qiskit instruction properties dictionary for the given IQM native operation.

            Currently we do not provide any actual properties for the operation other than the
            allowed loci.
            """
            loci = operations[op_name]
            if symmetric:
                # For symmetric gates, construct all the valid loci for Qiskit.
                # Coupling maps in Qiskit are directed graphs, and gate symmetry is provided explicitly.
                loci = [permuted_locus for locus in loci for permuted_locus in itertools.permutations(locus)]
            return {tuple(qb_to_idx[qb] for qb in locus): None for locus in loci}

        if 'measure' in operations:
            target.add_instruction(Measure(), _create_properties('measure'))
        target.add_instruction(IGate(), {(qb_to_idx[qb],): None for qb in architecture.qubits})
        if 'prx' in operations:
            target.add_instruction(RGate(Parameter('theta'), Parameter('phi')), _create_properties('prx'))
        if 'cz' in operations:
            target.add_instruction(CZGate(), _create_properties('cz', symmetric=True))
        if 'move' in operations:
            target.add_instruction(MoveGate(), _create_properties('move'))

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
        """Given an IQM-style qubit name, return the corresponding index in the register.

        Args:
            name: IQM-style qubit name ('QB1', 'QB2', etc.)

        Returns:
            Index of the given qubit in the quantum register,
            or ``None`` if the given qubit is not found on the backend.
        """
        return self._qb_to_idx.get(name)

    def index_to_qubit_name(self, index: int) -> Optional[str]:
        """Given a quantum register index, return the corresponding IQM-style qubit name.

        Args:
            index: Qubit index in the quantum register.

        Returns:
            Corresponding IQM-style qubit name ('QB1', 'QB2', etc.), or ``None`` if
            the given index does not correspond to any qubit on the backend.
        """
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
