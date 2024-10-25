# Copyright 2024 Qiskit on IQM developers
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
"""A layout algorithm that generates an initial layout for a quantum circuit that is
valid on the quantum architecture specification of the given IQM backend."""
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import PassManager, TranspilerError
from qiskit.transpiler.passes import TrivialLayout

from iqm.qiskit_iqm.iqm_provider import IQMBackend


class IQMMoveLayout(TrivialLayout):
    r"""Creates a qubit layout that is valid on the quantum architecture specification of the
    given IQM backend with regard to the move gate. In more detail, assumes that the move
    operations in the quantum architecture define which physical qubit is the resonator and
    which is a move qubit, and shuffles the logical indices of the circuit so that they match
    the requirements.

    This is required because Qiskit's basic layout algorithm assumes each connection between
    two qubits has the same gates defined.

    Note: This simple version of the mapper only works reliably with a single move qubit
    and resonator, and only if the circuit contains at least one move gate."""

    def __init__(self, backend: IQMBackend):
        super().__init__(backend.target)
        self._backend = backend

    def run(self, dag):
        """Creates the qubit layout for the given quantum circuit.

        Args:
            dag (DAGCircuit): DAG to find layout for.

        Raises:
            TranspilerError: if dag wider than the target backend or if a valid mapping could not be found
        """
        # Run TrivialLayout to get the initial 1-to-1 mapping
        super().run(dag)

        changes = self._determine_required_changes(dag)
        if len(changes) < 1:
            # No need to shuffle any qubits
            return

        layout = self.get_initial_layout()
        for src, dst in changes:
            layout.swap(src, dst)

        self.property_set['layout'] = layout

    def get_initial_layout(self):
        """Returns the initial layout generated by the algorithm.

        Returns:
            the initial layout
        """
        return self.property_set['layout']

    def _determine_required_changes(self, dag: DAGCircuit) -> list[tuple[int, int]]:
        """Scans the operations in the given circuit and determines what qubits
        need to be switched so that the operations are valid for the specified quantum architecture.

        Args:
            dag - the circuit to check

        Returns:
            the list of required changes as tuples of logical indices that should be switched;
            empty list if no changes are required.
        """
        reqs = self._calculate_requirements(dag)
        types = self._get_qubit_types()

        changes: list[tuple[int, int]] = []
        for index, qubit_type in reqs.items():
            if index not in types or qubit_type != types[index]:
                # Need to change qubit at index to qubit_type
                matching_qubit = next((i for i, t in types.items() if t == qubit_type), None)
                if matching_qubit is None:
                    raise TranspilerError(f"Cannot find a '{qubit_type}' from the quantum architecture.")
                changes.append((index, matching_qubit))
        return changes

    def _get_qubit_types(self) -> dict[int, str]:
        """Determines the types of qubits in the quantum architecture.

        Returns:
            a dictionary mapping logical indices to qubit types for those
            qubits where the type is relevant.
        """
        backend = self._backend
        qubit_types: dict[int, str] = {}
        for gate_name, gate_info in backend.architecture.gates.items():
            if gate_name == 'move':
                for locus in gate_info.loci:
                    [qubit, resonator] = [backend.qubit_name_to_index(q) for q in locus]
                    if qubit is not None:
                        qubit_types[qubit] = 'move_qubit'
                    if resonator is not None:
                        qubit_types[resonator] = 'resonator'

        return qubit_types

    @staticmethod
    def _calculate_requirements(dag: DAGCircuit) -> dict[int, str]:
        """Calculates the requirements for each logical qubit in the circuit.

        Args:
            dag - the circuit to check

        Returns:
            A mapping of the logical qubit indices to the required type for that qubit.
        """
        required_types: dict[int, str] = {}

        def _require_type(qubit_index: int, required_type: str, instruction_name: str):
            if qubit_index in required_types and required_types[qubit_index] != required_type:
                raise TranspilerError(
                    f"""Invalid target '{qubit_index}' for the '{instruction_name}' operation,
                    qubit {qubit_index} would need to be {required_type} but it is already required to be
                    '{required_types[qubit_index]}'."""
                )
            required_types[qubit_index] = required_type

        for node in dag.topological_op_nodes():
            if node.name == 'move':
                # The move operation requires that the first operand is the move qubit,
                # and the second must be the resonator
                (qubit, resonator) = node.qargs
                _require_type(dag.qubits.index(qubit), 'move_qubit', 'move')
                _require_type(dag.qubits.index(resonator), 'resonator', 'move')

        return required_types


def generate_initial_layout(backend: IQMBackend, circuit: QuantumCircuit):
    """Generates the initial layout for the given circuit, when run against the given backend.

    Args:
        backend - the IQM backend to run against
        circuit - the circuit for which a layout is to be generated

    Returns:
        a layout that remaps the qubits so that the move qubit and the resonator are using the correct
        indices.
    """
    layout_gen = IQMMoveLayout(backend)
    pm = PassManager(layout_gen)
    pm.run(circuit)
    return layout_gen.get_initial_layout()
