# Copyright 2024-2025 Qiskit on IQM developers
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
"""Generate an initial layout for a quantum circuit that is
valid on the quantum architecture specification of the given backend."""
from typing import Optional, Union

from qiskit import QuantumCircuit
from qiskit.circuit import Qubit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import PassManager, TranspilerError
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.passes import TrivialLayout

from iqm.qiskit_iqm.iqm_backend import IQMBackendBase


class IQMMoveLayout(TrivialLayout):
    """Create a layout that is valid on the dynamic quantum architecture of the
    given IQM target.

    The architecture defines which gate loci are available. This class
    tries to map the virtual/logical components of the circuit to the physical QPU components
    of the architecture, such that the gates in the circuit can be applied on those components.

    This class is required because Qiskit's basic layout algorithm assumes all connections between
    two qubits have the same two-qubit gates available, which isn't true in general.

    .. note::

       This version of the layout generator only works reliably with a single resonator,
       and can only handle pure Star architecture circuits.
       It also assumes that a valid layout exists for the circuit that does not require SWAPs, which
       isn't true in general.
    """

    def run(self, dag: DAGCircuit):
        """Creates a valid layout for the given quantum circuit.

        Args:
            dag: Circuit DAG to find layout for.

        Raises:
            TranspilerError: A valid layout could not be found.
        """
        target = self.target

        # NOTE assumes we use the real Star architecture here
        reqs, resonators = self._calculate_requirements(dag)
        if len(resonators) > 1:
            raise TranspilerError(
                'Circuit requires more than one computational resonator, IQMMoveLayout cannot yet handle this.'
            )

        # map unused physical components to the gates they support
        free_qubits: dict[int, set[str]] = {}
        for op in ['move', 'cz', 'measure', 'r']:
            for locus in target.qargs_for_operation_name(op):
                # For arity-2 gates, we only care about the first locus component,
                # because in the Star architecture the second one is a resonator.
                free_qubits.setdefault(locus[0], set()).add(op)

        # Add reqs for unused logical components in the circuit (they require nothing) so they too end up in the layout.
        # They are assigned physical components only after all the used components have been assigned theirs, hence
        # they will not affect the satisfiability.
        for log_idx in range(len(dag.qubits)):
            if log_idx not in resonators:
                reqs.setdefault(log_idx, set())

        # mapping from physical component index to logical qubit
        layout: dict[int, Qubit] = {}
        # add the resonators to the layout
        # TODO if we require more than one resonator, the order in which we map them to physical resonators matters
        for log_idx, res_name in zip(resonators, target.iqm_dqa.computational_resonators):
            phys_idx = target.iqm_component_to_idx[res_name]
            layout = {phys_idx: dag.qubits[log_idx]}

        # add qubits to the layout
        for log_idx, req_ops in reqs.items():
            # which physical qubits have the required ops available?
            mapping_options = [(phys_idx, len(av_ops)) for phys_idx, av_ops in free_qubits.items() if req_ops <= av_ops]
            # pick the one that has the fewest unneeded ops
            # TODO this heuristic does not always find a possible layout! If there are two options, each with a
            # different unnecessary gate, we pick one essentially at random, which may mean that later we cannot
            # satisfy another logical component because we picked the wrong option.
            if not mapping_options:
                raise TranspilerError(
                    f'Cannot find a physical qubit to map logical qubit {log_idx} to, '
                    f'requires {req_ops}, available: {free_qubits}.'
                )
            phys_idx, _ = min(mapping_options, key=lambda x: x[1])
            layout[phys_idx] = dag.qubits[log_idx]
            del free_qubits[phys_idx]  # phys_idx is now taken

        self.property_set['layout'] = Layout(layout)

    def get_initial_layout(self) -> Layout:
        """Returns the initial layout generated by the algorithm.

        Returns:
            The initial layout.
        """
        return self.property_set['layout']

    @staticmethod
    def _calculate_requirements(dag: DAGCircuit) -> tuple[dict[int, set[str]], set[int]]:
        """Determine the requirements for each used logical qubit in the circuit.

        Because in the Star architecture two-qubit gates have (qubit, resonator) loci, based on them
        we can figure out which logical qubits must be mapped to computational resonators.

        Unused logical qubits do not appear in the circuit DAG, and thus are not included in the mapping.

        Args:
            dag: circuit to check

        Returns:
            Mapping of the logical qubit indices to the required gates for that qubit,
            logical qubit indices that must be resonators.
        """
        reqs: dict[int, set[str]] = {}
        resonators: set[int] = set()
        qubit_to_idx: dict[Qubit, int] = {qubit: log_idx for log_idx, qubit in enumerate(dag.qubits)}

        def _require_qubit_type(qubit: Qubit, required_type: str):
            """Add a requirement for the given qubit."""
            log_idx = qubit_to_idx[qubit]
            if log_idx in resonators:
                raise TranspilerError(
                    f"Virtual/logical qubit {qubit} for the '{node.name}' operation must be a qubit, "
                    f'but it is already required to be a resonator.'
                )
            reqs.setdefault(log_idx, set()).add(required_type)

        for node in dag.topological_op_nodes():
            if node.name in ('barrier',):
                continue
            if node.name in ('move', 'cz'):
                # In the real Star architecture, all arity-2 ops act on a (qubit, resonator) locus.
                qubit, resonator = node.qargs
                _require_qubit_type(qubit, node.name)
                # resonator
                log_idx = qubit_to_idx[resonator]
                if log_idx in reqs:
                    raise TranspilerError(
                        f"Virtual/logical qubit {resonator} for the '{node.name}' operation must be a resonator, "
                        f'but it is already required to be a qubit({reqs[log_idx]}).'
                    )
                resonators.add(log_idx)
            elif node.name == 'measure':
                _require_qubit_type(node.qargs[0], 'measure')
            else:
                # all single-qubit gates are mapped to r
                _require_qubit_type(node.qargs[0], 'r')

        return reqs, resonators


def generate_initial_layout(
    backend: IQMBackendBase,
    circuit: QuantumCircuit,
    restrict_to_qubits: Optional[Union[list[int], list[str]]] = None,
) -> Layout:
    """Generates an initial layout for the given circuit, when run against the given backend.

    Args:
        backend: IQM backend to run against.
        circuit: Star architecture circuit for which a layout is to be generated.
        restrict_to_qubits: Optional list of qubits to restrict the layout to.

    Returns:
        Layout that maps the logical qubits of ``circuit`` to the physical qubits of ``backend`` so that
        all the gates in ``circuit`` are available on those loci.
    """
    target = backend.get_real_target()
    if restrict_to_qubits is not None:
        target = target.restrict_to_qubits(restrict_to_qubits)

    layout_gen = IQMMoveLayout(target)
    pm = PassManager(layout_gen)
    pm.run(circuit)
    return layout_gen.get_initial_layout()
