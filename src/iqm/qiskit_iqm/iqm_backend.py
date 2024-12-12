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
from copy import deepcopy
import re
from typing import Final, List, Union
from uuid import UUID

from qiskit.circuit import Parameter, Reset
from qiskit.circuit.library import CZGate, IGate, Measure, RGate
from qiskit.providers import BackendV2
from qiskit.transpiler import Target

from iqm.iqm_client import (
    DynamicQuantumArchitecture,
    GateImplementationInfo,
    GateInfo,
    QuantumArchitectureSpecification,
)
from iqm.qiskit_iqm.move_gate import MoveGate

IQM_TO_QISKIT_GATE_NAME: Final[dict[str, str]] = {'prx': 'r', 'cz': 'cz'}


def _dqa_from_static_architecture(sqa: QuantumArchitectureSpecification) -> DynamicQuantumArchitecture:
    """Create a dynamic quantum architecture from the given static quantum architecture.

    Since the DQA contains some attributes that are not present in an SQA, they are filled with mock data:

    * Each gate type is given a single mock implementation.
    * Calibration set ID is set to the all-zeros UUID.

    Args:
        sqa: static quantum architecture to replicate
    Returns:
        DQA replicating the properties of ``sqa``
    """
    # NOTE this prefix-based heuristic for identifying the qubits and resonators is not always guaranteed to work
    qubits = [qb for qb in sqa.qubits if qb.startswith('QB')]
    computational_resonators = [qb for qb in sqa.qubits if qb.lower().startswith('comp')]
    gates = {
        gate_name: GateInfo(
            implementations={'__fake': GateImplementationInfo(loci=tuple(tuple(locus) for locus in gate_loci))},
            default_implementation='__fake',
            override_default_implementation={},
        )
        for gate_name, gate_loci in sqa.operations.items()
    }
    gates['measure'] = GateInfo(
        implementations={'__fake': GateImplementationInfo(loci=tuple(tuple([locus]) for locus in qubits))},
        default_implementation='__fake',
        override_default_implementation={},
    )
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('00000000-0000-0000-0000-000000000000'),
        qubits=qubits,
        computational_resonators=computational_resonators,
        gates=gates,
    )


def _component_sort_key(component_name: str) -> tuple[str, int, str]:
    def get_numeric_id(name: str) -> int:
        match = re.search(r'(\d+)', name)
        return int(match.group(1)) if match else 0

    return re.sub(r'[^a-zA-Z]', '', component_name), get_numeric_id(component_name), component_name


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

    architecture: DynamicQuantumArchitecture

    def __init__(
        self,
        architecture: Union[QuantumArchitectureSpecification, DynamicQuantumArchitecture],
        **kwargs,
    ):
        super().__init__(**kwargs)
        if isinstance(architecture, QuantumArchitectureSpecification):
            arch = _dqa_from_static_architecture(architecture)
        else:
            arch = architecture
        self.architecture = arch

        # Qiskit uses integer indices to refer to qubits, so we need to map component names to indices.
        # Because of the way the Target and the transpiler interact, the resonators need to have higher indices than
        # qubits, or else transpiling with optimization_level=0 will fail because of lacking resonator indices.
        qb_to_idx = {
            qb: idx
            for idx, qb in enumerate(
                sorted(arch.qubits, key=_component_sort_key)
                + sorted(arch.computational_resonators, key=_component_sort_key)
            )
        }

        self._target = IQMTarget(arch, qb_to_idx)
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}
        self.name = 'IQMBackend'
        self._coupling_map = self.target.build_coupling_map()

    @property
    def target(self) -> Target:
        return self._target

    @property
    def physical_qubits(self) -> list[str]:
        """Return the list of physical qubits in the backend."""
        return list(self._qb_to_idx)

    def has_resonators(self) -> bool:
        """Return whether the backend has resonators."""
        return bool(self.architecture.computational_resonators)

    def qubit_name_to_index(self, name: str) -> int:
        """Given an IQM-style qubit name, return the corresponding index in the register.

        Args:
            name: IQM-style qubit name ('QB1', 'QB2', etc.)

        Returns:
            Index of the given qubit in the quantum register.

        Raises:
            ValueError: Qubit name cannot be found on the backend.
        """
        if name not in self._qb_to_idx:
            raise ValueError(f'Qubit \'{name}\' is not found on the backend.')
        return self._qb_to_idx[name]

    def index_to_qubit_name(self, index: int) -> str:
        """Given a quantum register index, return the corresponding IQM-style qubit name.

        Args:
            index: Qubit index in the quantum register.

        Returns:
            Corresponding IQM-style qubit name ('QB1', 'QB2', etc.).

        Raises:
            ValueError: Qubit index cannot be found on the backend.
        """
        if index not in self._idx_to_qb:
            raise ValueError(f'Qubit index {index} is not found on the backend.')
        return self._idx_to_qb[index]

    def get_scheduling_stage_plugin(self) -> str:
        """Return the plugin that should be used for scheduling the circuits on this backend."""
        return 'iqm_default_scheduling'


class IQMTarget(Target):
    """A target representing an IQM backends that could have resonators.

    This target is used to represent the physical layout of the backend, including the resonators as well as a fake
    coupling map to present to the Qiskit transpiler.

    Args:
        architecture: The quantum architecture specification representing the backend.
        component_to_idx: A mapping from component names to integer indices.
    """

    def __init__(self, architecture: DynamicQuantumArchitecture, component_to_idx: dict[str, int]):
        super().__init__()
        self.iqm_dynamic_architecture = architecture
        self.iqm_component_to_idx = component_to_idx
        self.iqm_idx_to_component = {v: k for k, v in component_to_idx.items()}
        self.real_target = self._iqm_create_instructions(architecture, component_to_idx)

    def _iqm_create_instructions(self, architecture: DynamicQuantumArchitecture, component_to_idx: dict[str, int]):
        """Converts a QuantumArchitectureSpecification object to a Qiskit Target object.

        Args:
            architecture: The quantum architecture specification to convert.

        Returns:
            A Qiskit Target object representing the given quantum architecture specification.
        """
        # pylint: disable=too-many-branches
        operations = architecture.gates

        # There is no dedicated direct way of setting just the qubit connectivity and the native gates to the target.
        # Such info is automatically deduced once all instruction properties are set. Currently, we do not retrieve
        # any properties from the server, and we are interested only in letting the target know what is the native gate
        # set and the connectivity of the device under use. Thus, we populate the target with None properties.
        def _create_connections(name: str, is_symmetric: bool = False) -> dict[tuple[int, ...], None]:
            """Creates the connection map of allowed loci for this instruction, mapped to None."""
            gate_info = operations[name]
            all_loci = gate_info.implementations[gate_info.default_implementation].loci
            connections = {tuple(component_to_idx[locus] for locus in loci): None for loci in all_loci}
            if is_symmetric:
                # If the gate is symmetric, we need to add the reverse connections as well.
                connections.update({tuple(reversed(loci)): None for loci in connections})
            return connections

        if 'prx' in operations or 'phased_rx' in operations:
            self.add_instruction(
                RGate(Parameter('theta'), Parameter('phi')),
                _create_connections('prx'),
            )
        if 'cc_prx' in operations:
            # HACK reset gate shares cc_prx loci for now
            self.add_instruction(Reset(), _create_connections('cc_prx'))

        self.add_instruction(
            IGate(),
            {(component_to_idx[qb],): None for qb in architecture.computational_resonators + architecture.qubits},
        )
        # Even though CZ is a symmetric gate, we still need to add properties for both directions. This is because
        # coupling maps in Qiskit are directed graphs and the gate symmetry is not implicitly planted there. It should
        # be explicitly supplied. This allows Qiskit to have coupling maps with non-symmetric gates like cx.
        if 'measure' in operations:
            self.add_instruction(Measure(), _create_connections('measure'))

        # Special work for devices with a MoveGate.
        real_target: IQMTarget = deepcopy(self)

        if 'move' in operations:
            real_target.add_instruction(MoveGate(), _create_connections('move'))

        fake_target_with_moves = deepcopy(real_target)
        if 'cz' in operations:
            real_target.add_instruction(CZGate(), _create_connections('cz', True))
            if 'move' in operations:
                fake_cz_connections: dict[tuple[int, int], None] = {}
                cz_loci = operations['cz'].implementations[operations['cz'].default_implementation].loci
                move_cz_connections: dict[tuple[int, int], None] = {}
                for qb1, qb2 in cz_loci:
                    if (
                        qb1 not in architecture.computational_resonators
                        and qb2 not in architecture.computational_resonators
                    ):
                        fake_cz_connections[(component_to_idx[qb1], component_to_idx[qb2])] = None
                        fake_cz_connections[(component_to_idx[qb2], component_to_idx[qb1])] = None
                    else:
                        move_cz_connections[(component_to_idx[qb1], component_to_idx[qb2])] = None
                        move_cz_connections[(component_to_idx[qb2], component_to_idx[qb1])] = None
                for qb1, res in operations['move'].implementations[operations['move'].default_implementation].loci:
                    for qb2 in [q for q in architecture.qubits if q not in [qb1, res]]:
                        if (qb2, res) in cz_loci or (res, qb2) in cz_loci:
                            fake_cz_connections[(component_to_idx[qb1], component_to_idx[qb2])] = None
                            fake_cz_connections[(component_to_idx[qb2], component_to_idx[qb1])] = None
                self.add_instruction(CZGate(), fake_cz_connections)
                fake_cz_connections.update(move_cz_connections)
                fake_target_with_moves.add_instruction(CZGate(), fake_cz_connections)
            else:
                self.add_instruction(CZGate(), _create_connections('cz', True))
                fake_target_with_moves.add_instruction(CZGate(), _create_connections('cz', True))
        fake_target_with_moves.set_real_target(real_target)
        self.fake_target_with_moves: IQMTarget = fake_target_with_moves
        return real_target

    def set_real_target(self, real_target: IQMTarget) -> None:
        """Set the real target for this target.

        Args:
            real_target: The real target to set.
        """
        self.real_target = real_target

    def restrict_to_qubits(self, qubits: Union[List[int], List[str]]) -> IQMTarget:
        """Restrict the target to only the given qubits.

        Args:
            qubits: The qubits to restrict the target to. Can be either a list of qubit indices or qubit names.
        """
        qubits_str = [self.iqm_idx_to_component[q] if isinstance(q, int) else str(q) for q in qubits]
        new_gates = {}
        for gate_name, gate_info in self.iqm_dynamic_architecture.gates.items():
            new_implementations = {}
            for implementation_name, implementation_info in gate_info.implementations.items():
                new_loci = [loci for loci in implementation_info.loci if all(q in qubits_str for q in loci)]
                if new_loci:
                    new_implementations[implementation_name] = GateImplementationInfo(loci=new_loci)
            if new_implementations:
                new_gates[gate_name] = GateInfo(
                    implementations=new_implementations,
                    default_implementation=gate_info.default_implementation,
                    override_default_implementation=gate_info.override_default_implementation,
                )
        new_arch = DynamicQuantumArchitecture(
            calibration_set_id=self.iqm_dynamic_architecture.calibration_set_id,
            qubits=[q for q in qubits_str if q in self.iqm_dynamic_architecture.qubits],
            computational_resonators=[
                q for q in qubits_str if q in self.iqm_dynamic_architecture.computational_resonators
            ],
            gates=new_gates,
        )
        return IQMTarget(new_arch, {name: idx for idx, name in enumerate(qubits_str)})
