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
from iqm.iqm_client.transpile import simplify_architecture
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
        architecture: Quantum architecture associated with the backend instance.
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

        full_target = IQMTarget(arch)

        if arch.computational_resonators:
            # Create a simplified target for the Qiskit transpiler that does not involve resonators,
            # but instead implements qubit-resonator gates as fictional qubit-qubit gates whereever possible.
            self._target = IQMTarget(arch, simplify=True)
            self._full_target = full_target
        else:
            self._target = full_target
            self._full_target = None

        self._qb_to_idx = full_target.iqm_component_to_idx
        self._idx_to_qb = full_target.iqm_idx_to_component
        self.name = 'IQMBackend'
        self._coupling_map = self.target.build_coupling_map()

    @property
    def target(self) -> Target:
        return self._target

    @property
    def target_with_resonators(self) -> Target:
        """Return the target with MOVE gates and resonators included."""
        if self._full_target is None:
            return self.target
        return self._full_target

    @property
    def physical_qubits(self) -> list[str]:
        """Return the list of physical qubits in the backend."""
        return list(self._qb_to_idx)

    def has_resonators(self) -> bool:
        """True iff the backend QPU has computational resonators."""
        return bool(self.architecture.computational_resonators)

    def get_real_target(self) -> Target:
        """Return the real physical target of the backend without fictional gates."""
        return IQMTarget(self.architecture)

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
        self, qubits: Union[list[int], list[str]],
    ) -> IQMTarget:
        """Generated a restricted transpilation target from this backend that only contains the given qubits.

        Args:
            qubits: Qubits to restrict the target to. Can be either a list of qubit indices or qubit names.

        Returns:
            restricted target
        """
        qubits_str = [self._idx_to_qb[q] if isinstance(q, int) else str(q) for q in qubits]
        return _restrict_dqa_to_components(self.architecture, qubits_str)


def _restrict_dqa_to_components(
    architecture: DynamicQuantumArchitecture,
    components: list[str],
) -> IQMTarget:
    """Generated a restricted transpilation target from this backend that only contains the given components.

    Args:
        architecture: Quantum architecture to restrict.
        components: Components to restrict the target to. Can be either a list of qubit indices or qubit names.

    Returns:
        target corresponding to ``architecture``, restricted
    """
    components_set = frozenset(components)

    def is_valid(locus: Locus) -> bool:
        """All components of the given locus belong to components_set."""
        return set(locus) <= components_set

    # filter out the loci which do not belong to the restricted component set
    new_gates = {}
    for gate_name, gate_info in architecture.gates.items():
        new_implementations = {}
        for implementation_name, implementation_info in gate_info.implementations.items():
            new_loci = tuple(locus for locus in implementation_info.loci if is_valid(locus))
            if new_loci:
                new_implementations[implementation_name] = GateImplementationInfo(loci=new_loci)
        if new_implementations:
            new_gates[gate_name] = GateInfo(
                implementations=new_implementations,
                default_implementation=gate_info.default_implementation,
                override_default_implementation={
                    locus: impl_name
                    for locus, impl_name in gate_info.override_default_implementation.items()
                    if is_valid(locus)
                },
            )
    new_arch = DynamicQuantumArchitecture(
        calibration_set_id=architecture.calibration_set_id,
        qubits=[q for q in architecture.qubits if q in components_set],
        computational_resonators=[r for r in architecture.computational_resonators if r in components_set],
        gates=new_gates,
    )
    return IQMTarget(new_arch)


class IQMTarget(Target):
    """Transpilation target for an IQM architecture.

    Args:
        architecture: Quantum architecture that defines the target.
        simplify: Iff True, abstract away computational resonators in the architecture.
    """

    def __init__(
        self,
        architecture: DynamicQuantumArchitecture,
        *,
        simplify: bool = False,
    ):
        super().__init__()

        # Using iqm as a prefix to avoid name clashes with the base class.
        self.iqm_dqa = architecture  # real architecture

        # Qiskit uses integer indices to refer to qubits, so we need to map component names to indices.
        # Because of the way the Target and the transpiler interact, the resonators need to have higher indices than
        # qubits, or else transpiling with optimization_level=0 will fail because of lacking resonator indices.
        component_to_idx = {c: idx for idx, c in enumerate(architecture.qubits + architecture.computational_resonators)}
        self.iqm_component_to_idx = component_to_idx
        self.iqm_idx_to_component = {v: k for k, v in component_to_idx.items()}

        simple = simplify_architecture(architecture)
        # should we abstract away the computational resonators?
        if simplify:
            # just use the simple arch
            architecture = simple
        else:
            # union of the simple arch and the real arch (modifying it! FIXME?)
            for name, gate_info in simple.gates.items():
                impl = gate_info.implementations.get('__fictional')
                if impl is not None:
                    gate_info_real = architecture.gates[name]
                    gate_info_real.implementations['__fictional'] = impl


        # mapping from op name to all its allowed loci
        op_loci = {gate_name: gate_info.loci for gate_name, gate_info in architecture.gates.items()}

        def locus_to_idx(locus: Locus) -> LocusIdx:
            """Map the given locus to use component indices instead of component names."""
            return tuple(component_to_idx[component] for component in locus)

        def create_properties(name: str, *, symmetrize: bool = False) -> dict[LocusIdx, None]:
            """Creates the Qiskit instruction properties dictionary for the given IQM native operation.

            Currently we do not provide any actual properties for the operation, hence the all the
            allowed loci map to None.
            """
            loci = op_loci[name]
            if symmetrize:
                # symmetrize the loci FIXME probaby not necessary, qiskit transpiler understands symmetric gates
                loci = tuple(permuted_locus for locus in loci for permuted_locus in itertools.permutations(locus))
            return {locus_to_idx(locus): None for locus in loci}

        ## Special gates/ops which are always available and do not appear in the architecture.

        # like barrier, delay is always available for all single-qubit loci
        self.add_instruction(Delay(0), {locus_to_idx((q,)): None for q in architecture.qubits})

        # identity gate does nothing and is removed in serialization, so we may as well allow it
        self.add_instruction(IGate(), {locus_to_idx((c,)): None for c in architecture.components})

        # Normal gates/ops that must appear in the architecture.
        IQM_TO_QISKIT = {
            'measure': Measure(),
            'prx': RGate(Parameter('theta'), Parameter('phi')),
            'cc_prx': Reset(),  # HACK reset gate shares cc_prx loci for now
            'cz': CZGate(),
            'move': MoveGate(),
        }
        for name, qiskit_gate in IQM_TO_QISKIT.items():
            if name in op_loci:
                self.add_instruction(qiskit_gate, create_properties(name))


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
        return _restrict_dqa_to_components(self.iqm_dqa, qubits_str)
