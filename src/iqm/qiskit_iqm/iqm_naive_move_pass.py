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
"""Naive transpilation for the IQM Star architecture."""
from typing import Optional, Union
import warnings

from pydantic_core import ValidationError
from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.layout import Layout

from iqm.iqm_client import Circuit as IQMClientCircuit
from iqm.iqm_client.transpile import ExistingMoveHandlingOptions, transpile_insert_moves

from .iqm_backend import IQMBackendBase, IQMTarget
from .iqm_move_layout import generate_initial_layout
from .qiskit_to_iqm import deserialize_instructions, serialize_instructions


class IQMNaiveResonatorMoving(TransformationPass):
    """WIP Naive transpilation pass for resonator moving

    A naive transpiler pass for use with the Qiskit PassManager.
    Although it requires a CouplingMap, Target, or Backend, it does not take this into account when adding MOVE gates.
    It assumes target connectivity graph is star shaped with a single resonator in the middle.
    The pass assumes that all single qubit and two-qubit gates are allowed.
    The resonator is used to swap the qubit states for the two-qubit gates.
    Additionally, it assumes that no single qubit gates are allowed on the resonator.

    Args:
        target: Transpilation target.
        existing_moves_handling: How to handle existing MOVE gates in the circuit.
    """

    def __init__(
        self,
        target: IQMTarget,
        existing_moves_handling: ExistingMoveHandlingOptions = ExistingMoveHandlingOptions.KEEP,
    ):
        super().__init__()
        self.architecture = target.iqm_dqa
        self.idx_to_component = target.iqm_idx_to_component
        self.component_to_idx = target.iqm_component_to_idx
        self.existing_moves_handling = existing_moves_handling

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the pass on a circuit.

        Args:
            dag: DAG to map.

        Returns:
            Mapped ``dag``.

        Raises:
            TranspilerError: The layout is not compatible with the DAG, or if the input gate set is incorrect.
        """
        print("Transpiling circuit")
        print(self.property_set)
        circuit = dag_to_circuit(dag)
        if len(circuit) == 0:
            return dag  # Empty circuit, no need to transpile.
        print(circuit)
        # For some reason, the dag does not contain the layout, so we need to do a bunch of fixing.
        if self.property_set.get("layout"):
            layout = self.property_set["layout"]
        else:
            layout = Layout.generate_trivial_layout(circuit)
        iqm_circuit = IQMClientCircuit(
            name="Transpiling Circuit",
            instructions=tuple(serialize_instructions(circuit, self.idx_to_component)),
        )
        try:
            routed_iqm_circuit = transpile_insert_moves(
                iqm_circuit, self.architecture, existing_moves=self.existing_moves_handling
            )
            routed_circuit = deserialize_instructions(
                list(routed_iqm_circuit.instructions), self.component_to_idx, layout
            )
        except ValidationError as e:  # The Circuit without move gates is empty.
            errors = e.errors()
            if (
                len(errors) == 1
                and errors[0]["msg"] == "Value error, Each circuit should have at least one instruction."
            ):
                circ_args = [circuit.num_ancillas, circuit.num_clbits]
                routed_circuit = QuantumCircuit(*layout.get_registers(), *(arg for arg in circ_args if arg > 0))
            else:
                raise e
        # Create the new DAG and make sure that the qubits are properly ordered.
        ordered_qubits = [layout.get_physical_bits()[i] for i in range(len(layout.get_physical_bits()))]
        new_dag = circuit_to_dag(routed_circuit, qubit_order=ordered_qubits, clbit_order=routed_circuit.clbits)
        # Update the final_layout with the correct bits.
        if "final_layout" in self.property_set:
            inv_layout = layout.get_physical_bits()
            self.property_set["final_layout"] = Layout(
                {
                    physical: inv_layout[dag.find_bit(virtual).index]
                    for physical, virtual in self.property_set["final_layout"].get_physical_bits().items()
                }
            )
        else:
            self.property_set["final_layout"] = layout
        print(self.property_set["final_layout"])
        return new_dag


def transpile_to_IQM(  # pylint: disable=too-many-arguments
    circuit: QuantumCircuit,
    backend: IQMBackendBase,
    target: Optional[IQMTarget] = None,
    initial_layout: Optional[Union[Layout, dict, list]] = None,
    perform_move_routing: bool = True,
    optimize_single_qubits: bool = True,
    ignore_barriers: bool = False,
    remove_final_rzs: bool = True,
    existing_moves_handling: Optional[ExistingMoveHandlingOptions] = None,
    restrict_to_qubits: Optional[Union[list[int], list[str]]] = None,
    **qiskit_transpiler_kwargs,
) -> QuantumCircuit:
    """Customized transpilation to IQM backends.

    Works with both the Crystal and Star architectures.

    Args:
        circuit: The circuit to be transpiled without MOVE gates.
        backend: The target backend to compile to. Does not require a resonator.
        target: An alternative target to compile to than the backend, using this option requires intimate knowledge
            of the transpiler and thus it is not recommended to use.
        initial_layout: The initial layout to use for the transpilation, same as :func:`~qiskit.compiler.transpile`.
        perform_move_routing: Whether to perform MOVE gate routing.
        optimize_single_qubits: Whether to optimize single qubit gates away.
        ignore_barriers: Whether to ignore barriers when optimizing single qubit gates away.
        remove_final_rzs: Whether to remove the final z rotations. It is recommended always to set this to true as
        the final RZ gates do no change the measurement outcomes of the circuit.
        existing_moves_handling: How to handle existing MOVE gates in the circuit, required if the circuit contains
            MOVE gates.
        restrict_to_qubits: Restrict the transpilation to only use these specific physical qubits. Note that you will
            have to pass this information to the ``backend.run`` method as well as a dictionary.
        qiskit_transpiler_kwargs: Arguments to be passed to the Qiskit transpiler.

    Returns:
        Transpiled circuit ready for running on the backend.
    """
    # pylint: disable=too-many-branches

    if restrict_to_qubits is not None:
        restrict_to_qubits = [backend.qubit_name_to_index(q) if isinstance(q, str) else q for q in restrict_to_qubits]

    if target is None:
        if circuit.count_ops().get("move", 0) > 0:
            target = backend.target_with_resonators
            # Create a sensible initial layout if none is provided
            if initial_layout is None:
                initial_layout = generate_initial_layout(backend, circuit, restrict_to_qubits)
            if perform_move_routing and existing_moves_handling is None:
                raise ValueError("The circuit contains MOVE gates but existing_moves_handling is not set.")
        else:
            target = backend.target

    if restrict_to_qubits is not None:
        target = target.restrict_to_qubits(restrict_to_qubits)

    # Determine which scheduling method to use
    scheduling_method = qiskit_transpiler_kwargs.pop("scheduling_method", None)
    if scheduling_method is None:
        if perform_move_routing:
            if optimize_single_qubits:
                if not remove_final_rzs:
                    scheduling_method = "move_routing_exact_global_phase"
                elif ignore_barriers:
                    scheduling_method = "move_routing_rz_optimization_ignores_barriers"
                else:
                    scheduling_method = "move_routing"
            else:
                scheduling_method = "only_move_routing"
            if existing_moves_handling is not None:
                if not scheduling_method.endswith("routing"):
                    raise ValueError(
                        "Existing Move handling options are not compatible with `remove_final_rzs` and \
                        `ignore_barriers` options."
                    )  # No technical reason for this, just hard to maintain all combinations.
                scheduling_method += "_" + existing_moves_handling.value
        else:
            if optimize_single_qubits:
                scheduling_method = "only_rz_optimization"
                if not remove_final_rzs:
                    scheduling_method += "_exact_global_phase"
                elif ignore_barriers:
                    scheduling_method += "_ignores_barriers"
            else:
                scheduling_method = "default"
    else:
        warnings.warn(
            f"Scheduling method is set to {scheduling_method}, but it is normally used to pass other transpiler "
            + "options, ignoring the `perform_move_routing`, `optimize_single_qubits`, `remove_final_rzs`, "
            + "`ignore_barriers`, and `existing_moves_handling` arguments."
        )
    qiskit_transpiler_kwargs["scheduling_method"] = scheduling_method
    new_circuit = transpile(circuit, target=target, initial_layout=initial_layout, **qiskit_transpiler_kwargs)
    return new_circuit
