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
import itertools
from typing import Final, Union
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

Locus = tuple[str, ...]
LocusIdx = tuple[int, ...]


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
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('00000000-0000-0000-0000-000000000000'),
        qubits=qubits,
        computational_resonators=computational_resonators,
        gates=gates,
    )


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

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
        self.architecture: DynamicQuantumArchitecture = arch
        """Dynamic quantum architecture of the backend instance."""

        # Qiskit uses integer indices to refer to qubits, so we need to map component names to indices.
        # Because of the way the Target and the transpiler interact, the resonators need to have higher indices than
        # qubits, or else transpiling with optimization_level=0 will fail because of lacking resonator indices.
        qb_to_idx = {qb: idx for idx, qb in enumerate(arch.qubits + arch.computational_resonators)}

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
        """True iff the backend QPU has computational resonators."""
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
    """Transpiler target representing an IQM backend that can have computational resonators.

    This target represents the physical layout of the backend including the resonators, as
    well as a fake coupling map without them to present to the Qiskit transpiler.

    Args:
        architecture: Represents the gates (and their loci) available for the transpilation.
        component_to_idx: Mapping from QPU component names to integer indices used by Qiskit to refer to them.
    """

    def __init__(self, architecture: DynamicQuantumArchitecture, component_to_idx: dict[str, int]):
        super().__init__()
        self.iqm_dqa = architecture
        self.iqm_component_to_idx = component_to_idx
        self.iqm_idx_to_component = {v: k for k, v in component_to_idx.items()}
        self.real_target: IQMTarget = self._iqm_create_instructions(architecture, component_to_idx)

    def _iqm_create_instructions(
        self, architecture: DynamicQuantumArchitecture, component_to_idx: dict[str, int]
    ) -> Target:
        """Converts a QuantumArchitectureSpecification object to a Qiskit Target object.

        Args:
            architecture: The quantum architecture specification to convert.
            component_to_idx: Mapping from QPU component names to integer indices used by Qiskit to refer to them.

        Returns:
            A Qiskit Target object representing the given quantum architecture specification.
        """
        # pylint: disable=too-many-branches,too-many-nested-blocks
        # mapping from op name to all its allowed loci
        op_loci = {gate_name: gate_info.loci for gate_name, gate_info in architecture.gates.items()}

        def locus_to_idx(locus: Locus) -> LocusIdx:
            """Map the given locus to use component indices instead of component names."""
            return tuple(component_to_idx[component] for component in locus)

        def create_properties(name: str, *, symmetrize: bool = False) -> dict[tuple[int, ...], None]:
            """Creates the Qiskit instruction properties dictionary for the given IQM native operation.

            Currently we do not provide any actual properties for the operation, hence the all the
            allowed loci map to None.
            """
            loci = op_loci[name]
            if symmetrize:
                # symmetrize the loci
                loci = tuple(permuted_locus for locus in loci for permuted_locus in itertools.permutations(locus))
            return {locus_to_idx(locus): None for locus in loci}

        if 'measure' in op_loci:
            self.add_instruction(Measure(), create_properties('measure'))

        # identity gate does nothing and is removed in serialization, so we may as well allow it everywhere
        self.add_instruction(
            IGate(),
            {locus_to_idx((component,)): None for component in architecture.components},
        )

        if 'prx' in op_loci:
            self.add_instruction(
                RGate(Parameter('theta'), Parameter('phi')),
                create_properties('prx'),
            )

        # HACK reset gate shares cc_prx loci for now
        if 'cc_prx' in op_loci:
            self.add_instruction(Reset(), create_properties('cc_prx'))

        # Special work for devices with a MoveGate.
        real_target: IQMTarget = deepcopy(self)

        if 'move' in op_loci:
            real_target.add_instruction(MoveGate(), create_properties('move'))

        fake_target_with_moves = deepcopy(real_target)
        # self has just single-q stuff, fake and real also have MOVE

        if 'cz' in op_loci:
            real_target.add_instruction(CZGate(), create_properties('cz'))

            if 'move' in op_loci:
                # CZ and MOVE: star
                fake_cz_connections: dict[LocusIdx, None] = {}
                move_cz_connections: dict[LocusIdx, None] = {}
                cz_loci = op_loci['cz']
                for c1, c2 in cz_loci:
                    idx_locus = locus_to_idx((c1, c2))
                    if (
                        c1 not in architecture.computational_resonators
                        and c2 not in architecture.computational_resonators
                    ):
                        # cz between two qubits TODO not possible in Star
                        # every cz locus that only uses qubits goes to fake_cz_conn
                        fake_cz_connections[idx_locus] = None
                    else:
                        # otherwise it goes to move_cz_conn
                        move_cz_connections[idx_locus] = None

                for c1, res in op_loci['move']:
                    for c2 in architecture.qubits:
                        if c2 not in [c1, res]:
                            # loop over c2 that is not c1
                            if (c2, res) in cz_loci or (res, c2) in cz_loci:
                                # This is a fake CZ and can be bidirectional.
                                # cz routable via res between qubits, put into fake_cz_conn both ways
                                idx_locus = locus_to_idx((c1, c2))
                                fake_cz_connections[idx_locus] = None
                                fake_cz_connections[idx_locus[::-1]] = None
                self.add_instruction(CZGate(), fake_cz_connections)  # self has fake cz conn
                fake_cz_connections.update(move_cz_connections)
                fake_target_with_moves.add_instruction(CZGate(), fake_cz_connections)
            else:
                # CZ but no MOVE: crystal
                self.add_instruction(CZGate(), create_properties('cz'))
                fake_target_with_moves.add_instruction(CZGate(), create_properties('cz'))
        fake_target_with_moves.real_target = real_target
        self.fake_target_with_moves: IQMTarget = fake_target_with_moves
        return real_target

    def restrict_to_qubits(self, qubits: Union[list[int], list[str]]) -> IQMTarget:
        """Restrict the transpilation target to only the given qubits.

        Args:
            qubits: Qubits to restrict the target to. Can be either a list of qubit indices or qubit names.

        Returns:
            restricted target
        """
        qubits_str = [self.iqm_idx_to_component[q] if isinstance(q, int) else str(q) for q in qubits]
        new_gates = {}
        for gate_name, gate_info in self.iqm_dqa.gates.items():
            new_implementations = {}
            for implementation_name, implementation_info in gate_info.implementations.items():
                new_loci = [locus for locus in implementation_info.loci if all(q in qubits_str for q in locus)]
                if new_loci:
                    new_implementations[implementation_name] = GateImplementationInfo(loci=new_loci)
            if new_implementations:
                new_gates[gate_name] = GateInfo(
                    implementations=new_implementations,
                    default_implementation=gate_info.default_implementation,
                    override_default_implementation=gate_info.override_default_implementation,
                )
        new_arch = DynamicQuantumArchitecture(
            calibration_set_id=self.iqm_dqa.calibration_set_id,
            qubits=[q for q in qubits_str if q in self.iqm_dqa.qubits],
            computational_resonators=[q for q in qubits_str if q in self.iqm_dqa.computational_resonators],
            gates=new_gates,
        )
        return IQMTarget(new_arch, {name: idx for idx, name in enumerate(qubits_str)})
