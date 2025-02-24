# Copyright 2022-2025 Qiskit on IQM developers
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
from typing import Final, Union
from uuid import UUID

from qiskit.circuit import Delay, Parameter, Reset
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
    gates = {
        gate_name: GateInfo(
            implementations={'__fake': GateImplementationInfo(loci=tuple(tuple(locus) for locus in gate_loci))},
            default_implementation='__fake',
            override_default_implementation={},
        )
        for gate_name, gate_loci in sqa.operations.items()
    }
    # NOTE that this heuristic for defining computational resonators is not perfect, but it should work for more cases
    # than the name-based heuristic. Computational_resonators will be mapped wrong if the resonator is not used in any
    # move gates.
    if 'move' in sqa.operations:
        computational_resonators = list({res for _, res in sqa.operations['move']})
    else:
        computational_resonators = []
    qubits = [qb for qb in sqa.qubits if qb not in computational_resonators]

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

        self._target = IQMTarget(arch, qb_to_idx, include_resonators=False)
        self._fake_target_with_moves = (
            IQMTarget(arch, qb_to_idx, include_resonators=True) if 'move' in arch.gates else None
        )
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}
        self.name = 'IQMBackend'
        self._coupling_map = self.target.build_coupling_map()

    @property
    def target(self) -> Target:
        return self._target

    @property
    def target_with_resonators(self) -> Target:
        """Return the target with MOVE gates and resonators included."""
        if self._fake_target_with_moves is None:
            return self.target
        return self._fake_target_with_moves

    @property
    def physical_qubits(self) -> list[str]:
        """Return the list of physical qubits in the backend."""
        return list(self._qb_to_idx)

    def has_resonators(self) -> bool:
        """True iff the backend QPU has computational resonators."""
        return bool(self.architecture.computational_resonators)

    def get_real_target(self) -> Target:
        """Return the real physical target of the backend without virtual CZ gates."""
        return IQMTarget(
            architecture=self.architecture,
            component_to_idx=self._qb_to_idx,
            include_resonators=True,
            include_fake_czs=False,
        )

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

    def restrict_to_qubits(
        self, qubits: Union[list[int], list[str]], include_resonators: bool = False, include_fake_czs: bool = True
    ) -> IQMTarget:
        """Generated a restricted transpilation target from this backend that only contains the given qubits.

        Args:
            qubits: Qubits to restrict the target to. Can be either a list of qubit indices or qubit names.
            include_resonators: Whether to restrict `self.target` or `self.target_with_resonators`.
            include_fake_czs: Whether to include virtual CZs that are unsupported, but could be routed via MOVE.

        Returns:
            restricted target
        """
        qubits_str = [self._idx_to_qb[q] if isinstance(q, int) else str(q) for q in qubits]
        return _restrict_dqa_to_qubits(self.architecture, qubits_str, include_resonators, include_fake_czs)


def _restrict_dqa_to_qubits(
    architecture: DynamicQuantumArchitecture, qubits: list[str], include_resonators: bool, include_fake_czs: bool = True
) -> IQMTarget:
    """Generated a restricted transpilation target from this backend that only contains the given qubits.

    Args:
        architecture: The dynamic quantum architecture to restrict.
        qubits: Qubits to restrict the target to. Can be either a list of qubit indices or qubit names.
        include_resonators: Whether to include MOVE gates in the target.
        include_fake_czs: Whether to include virtual CZs that are not natively supported, but could be routed via MOVE.

    Returns:
        restricted target
    """
    new_gates = {}
    for gate_name, gate_info in architecture.gates.items():
        new_implementations = {}
        for implementation_name, implementation_info in gate_info.implementations.items():
            new_loci = [locus for locus in implementation_info.loci if all(q in qubits for q in locus)]
            if new_loci:
                new_implementations[implementation_name] = GateImplementationInfo(loci=new_loci)
        if new_implementations:
            new_gates[gate_name] = GateInfo(
                implementations=new_implementations,
                default_implementation=gate_info.default_implementation,
                override_default_implementation=gate_info.override_default_implementation,
            )
    new_arch = DynamicQuantumArchitecture(
        calibration_set_id=architecture.calibration_set_id,
        qubits=[q for q in qubits if q in architecture.qubits],
        computational_resonators=[q for q in qubits if q in architecture.computational_resonators],
        gates=new_gates,
    )
    return IQMTarget(new_arch, {name: idx for idx, name in enumerate(qubits)}, include_resonators, include_fake_czs)


class IQMTarget(Target):
    """Transpilation target for an IQM architecture.

    Contains the mapping of physical qubit name on the device to qubit index in the Target.

    Args:
        architecture: Quantum architecture that defines the target.
        component_to_idx: Mapping from QPU component names to integer indices used by Qiskit to refer to them.
        include_resonators: Whether to include MOVE gates in the target.
        include_fake_czs: Whether to include virtual CZs that are not natively supported, but could be routed via MOVE.
    """

    def __init__(
        self,
        architecture: DynamicQuantumArchitecture,
        component_to_idx: dict[str, int],
        include_resonators: bool,
        include_fake_czs: bool = True,
    ):
        super().__init__()
        # Using iqm as a prefix to avoid name clashes with the base class.
        self.iqm_dqa = architecture
        self.iqm_component_to_idx = component_to_idx
        self.iqm_idx_to_component = {v: k for k, v in component_to_idx.items()}
        self.iqm_includes_resonators = include_resonators
        self.iqm_includes_fake_czs = include_fake_czs
        self._add_connections_from_DQA()

    def _add_connections_from_DQA(self):
        """Initializes the Target, making it represent the dynamic quantum architecture :attr:`iqm_dqa`."""
        # pylint: disable=too-many-branches,too-many-nested-blocks
        # mapping from op name to all its allowed loci
        architecture = self.iqm_dqa
        component_to_idx = self.iqm_component_to_idx
        op_loci = {gate_name: gate_info.loci for gate_name, gate_info in architecture.gates.items()}

        def locus_to_idx(locus: Locus) -> LocusIdx:
            """Map the given locus to use component indices instead of component names."""
            return tuple(component_to_idx[component] for component in locus)

        def create_properties(name: str, *, symmetrize: bool = False) -> dict[tuple[int, ...], None]:
            """Creates the Qiskit instruction properties dictionary for the given IQM native operation.

            Currently we do not provide any actual properties for the operation, hence the all the
            allowed loci map to None.
            """
            if self.iqm_includes_resonators:
                loci = op_loci[name]
            else:
                # Remove the loci that correspond to resonators.
                loci = [
                    locus for locus in op_loci[name] if all(component in self.iqm_dqa.qubits for component in locus)
                ]
            if symmetrize:
                # symmetrize the loci
                loci = tuple(permuted_locus for locus in loci for permuted_locus in itertools.permutations(locus))
            return {locus_to_idx(locus): None for locus in loci}

        # like barrier, delay is always available for all single-qubit loci
        self.add_instruction(Delay(0), {locus_to_idx((q,)): None for q in architecture.qubits})

        if 'measure' in op_loci:
            self.add_instruction(Measure(), create_properties('measure'))

        # identity gate does nothing and is removed in serialization, so we may as well allow it everywhere
        # Except if it is defined for the resonator, the graph is disconnected and the transpiler will fail.
        if self.iqm_includes_resonators:
            self.add_instruction(
                IGate(),
                {locus_to_idx((component,)): None for component in architecture.components},
            )
        else:
            self.add_instruction(
                IGate(),
                {locus_to_idx((component,)): None for component in architecture.qubits},
            )

        if 'prx' in op_loci:
            self.add_instruction(
                RGate(Parameter('theta'), Parameter('phi')),
                create_properties('prx'),
            )

        # HACK reset gate shares cc_prx loci for now
        if 'cc_prx' in op_loci:
            self.add_instruction(Reset(), create_properties('cc_prx'))

        if self.iqm_includes_resonators and 'move' in op_loci:
            self.add_instruction(MoveGate(), create_properties('move'))

        if 'cz' in op_loci:
            if self.iqm_includes_fake_czs and 'move' in op_loci:
                # CZ and MOVE: star
                cz_connections: dict[LocusIdx, None] = {}
                cz_loci = op_loci['cz']
                for c1, c2 in cz_loci:
                    if self.iqm_includes_resonators or all(component in self.iqm_dqa.qubits for component in (c1, c2)):
                        idx_locus = locus_to_idx((c1, c2))
                        cz_connections[idx_locus] = None

                for c1, res in op_loci['move']:
                    for c2 in architecture.qubits:
                        if c2 not in [c1, res]:
                            # loop over c2 that is not c1
                            if (c2, res) in cz_loci or (res, c2) in cz_loci:
                                # This is a fake CZ and can be bidirectional.
                                # cz routable via res between qubits, put into fake_cz_conn both ways
                                idx_locus = locus_to_idx((c1, c2))
                                cz_connections[idx_locus] = None
                                cz_connections[idx_locus[::-1]] = None
                self.add_instruction(CZGate(), cz_connections)
            else:
                # CZ but no MOVE: crystal
                self.add_instruction(CZGate(), create_properties('cz'))

    @property
    def physical_qubits(self) -> list[str]:
        """Return the ordered list of physical qubits in the backend."""
        # Overrides the property from the superclass to contain the correct information.
        return [self.iqm_idx_to_component[i] for i in range(self.num_qubits)]

    def restrict_to_qubits(self, qubits: Union[list[int], list[str]]) -> IQMTarget:
        """Generated a restricted transpilation target from this Target that only contains the given qubits.

        Args:
            qubits: Qubits to restrict the target to. Can be either a list of qubit indices or qubit names.

        Returns:
            restricted target
        """
        qubits_str = [self.iqm_idx_to_component[q] if isinstance(q, int) else str(q) for q in qubits]
        return _restrict_dqa_to_qubits(
            self.iqm_dqa, qubits_str, self.iqm_includes_resonators, self.iqm_includes_fake_czs
        )
