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
from dataclasses import dataclass
import itertools
from typing import Final, Optional, Union

from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, IGate, Measure, RGate
from qiskit.providers import BackendV2
from qiskit.transpiler import InstructionProperties, Target

from iqm.iqm_client import DynamicQuantumArchitecture, Locus, QuantumArchitectureSpecification
from iqm.qiskit_iqm.move_gate import MoveGate

IQM_TO_QISKIT_GATE_NAME: Final[dict[str, str]] = {'prx': 'r', 'cz': 'cz'}


@dataclass
class QuantumArchitecture:
    """A representation of the quantum computer architecture.

    Used to represent data from a DynamicQuantumArchitecture or a QuantumArchitectureSpecification in a unified way.
    """

    qubits: list[str]
    computational_resonators: list[str]
    gate_loci: dict[str, tuple[Locus, ...]]

    components = DynamicQuantumArchitecture.components

    @classmethod
    def from_static_architecture(cls, static_architecture: QuantumArchitectureSpecification) -> QuantumArchitecture:
        """Returns QuantumArchitecture created from the given static architecture."""
        qubits = [qb for qb in static_architecture.qubits if qb.startswith('QB')]
        computational_resonators = [qb for qb in static_architecture.qubits if qb.startswith('COMP')]
        gate_loci = {
            gate_name: tuple(tuple(locus) for locus in gate_loci)
            for gate_name, gate_loci in static_architecture.operations.items()
        }
        return QuantumArchitecture(
            qubits=qubits,
            computational_resonators=computational_resonators,
            gate_loci=gate_loci,
        )

    @classmethod
    def from_dynamic_architecture(cls, dynamic_architecture: DynamicQuantumArchitecture) -> QuantumArchitecture:
        """Returns QuantumArchitecture created from the given dynamic architecture."""
        return QuantumArchitecture(
            qubits=dynamic_architecture.qubits,
            computational_resonators=dynamic_architecture.computational_resonators,
            gate_loci={gate_name: gate_info.loci for gate_name, gate_info in dynamic_architecture.gates.items()},
        )


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

    architecture: QuantumArchitecture

    def __init__(
        self,
        architecture: Union[QuantumArchitectureSpecification, DynamicQuantumArchitecture],
        **kwargs,
    ):
        super().__init__(**kwargs)
        if isinstance(architecture, QuantumArchitectureSpecification):
            arch = QuantumArchitecture.from_static_architecture(architecture)
        else:
            arch = QuantumArchitecture.from_dynamic_architecture(architecture)
        self.architecture = arch

        qb_to_idx = {qb: idx for idx, qb in enumerate(arch.components)}  # type: ignore
        operations = {
            gate_name: [list(locus) for locus in gate_loci] for gate_name, gate_loci in arch.gate_loci.items()
        }

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
                loci = [list(permuted_locus) for locus in loci for permuted_locus in itertools.permutations(locus)]
            return {tuple(qb_to_idx[qb] for qb in locus): None for locus in loci}

        if 'measure' in operations:
            target.add_instruction(Measure(), _create_properties('measure'))
        target.add_instruction(
            IGate(),
            {(qb_to_idx[qb],): None for qb in arch.components},  # type: ignore
        )
        if 'prx' in operations:
            target.add_instruction(RGate(Parameter('theta'), Parameter('phi')), _create_properties('prx'))
        if 'cz' in operations:
            target.add_instruction(CZGate(), _create_properties('cz', symmetric=True))
        if 'move' in operations:
            target.add_instruction(MoveGate(), _create_properties('move'))

        self._target = target
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}
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
