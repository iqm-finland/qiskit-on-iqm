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
from typing import Optional

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import QuantumRegister, Qubit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import Layout, TranspileLayout
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passmanager import PassManager

from iqm.iqm_client import Circuit as IQMClientCircuit
from iqm.iqm_client.transpile import ExistingMoveHandlingOptions, transpile_insert_moves

from .iqm_backend import IQMBackendBase, IQMStarTarget
from .iqm_circuit import IQMCircuit
from .iqm_provider import _deserialize_instructions, _serialize_instructions
from .iqm_transpilation import IQMOptimizeSingleQubitGates


class IQMNaiveResonatorMoving(TransformationPass):
    """WIP Naive transpilation pass for resonator moving

    A naive transpiler pass for use with the Qiskit PassManager.
    Although it requires a CouplingMap, Target, or Backend, it does not take this into account when adding MoveGates.
    It assumes target connectivity graph is star shaped with a single resonator in the middle.
    Which qubit is the resonator is represented with the resonator_register attribute.
    The pass assumes that all single qubit and two-qubit gates are allowed.
    The resonator is used to swap the qubit states for the two-qubit gates.
    Additionally, it assumes that no single qubit gates are allowed on the resonator.
    """

    def __init__(
        self,
        target: IQMStarTarget,
        gate_set: list[str],
        existing_moves_handling: Optional[ExistingMoveHandlingOptions] = None,
    ):
        """WIP Naive transpilation pass for resonator moving

        Args:
            resonator_register (int): Which qubit/vertex index represents the resonator.
            move_qubits (int): Which qubits (indices) can be moved into the resonator.
            gate_set (list[str]): Which gates are allowed by the target backend.
        """
        super().__init__()
        self.target = target
        self.gate_set = gate_set
        self.existing_moves_handling = existing_moves_handling

    def run(self, dag: DAGCircuit):  # pylint: disable=too-many-branches
        """Run the IQMNaiveResonatorMoving pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to map.

        Returns:
            DAGCircuit: A mapped DAG.

        Raises:
            TranspilerError: if the layout are not compatible with the DAG, or if the input gate set is incorrect.
        """
        circuit = dag_to_circuit(dag)
        iqm_json = IQMClientCircuit(
            name="Transpiling Circuit",
            instructions=tuple(_serialize_instructions(circuit, self.target.iqm_idx_to_component)),
        )
        routed_json = transpile_insert_moves(
            iqm_json, self.target.iqm_dynamic_architecture, self.existing_moves_handling
        )
        routed_circuit = _deserialize_instructions(list(routed_json.instructions), self.target.iqm_component_to_idx)
        new_dag = circuit_to_dag(routed_circuit)
        return new_dag


def transpile_to_IQM(  # pylint: disable=too-many-arguments
    circuit: QuantumCircuit,
    backend: IQMBackendBase,
    optimize_single_qubits: bool = True,
    ignore_barriers: bool = False,
    remove_final_rzs: bool = True,
    **qiskit_transpiler_qwargs,
) -> QuantumCircuit:
    """Basic function for transpiling to IQM backends. Currently works with Deneb and Garnet

    Args:
        circuit: The circuit to be transpiled without MOVE gates.
        backend: The target backend to compile to. Does not require a resonator.
        optimize_single_qubits: Whether to optimize single qubit gates away.
        ignore_barriers: Whether to ignore barriers when optimizing single qubit gates away.
        remove_final_rzs: Whether to remove the final Rz rotations.
        qiskit_transpiler_qwargs: Arguments to be passed to the Qiskit transpiler.

    Raises:
        NotImplementedError: Thrown when the backend supports multiple resonators.

    Returns:
        QuantumCircuit: The transpiled circuit ready for running on the backend.
    """
    circuit_with_resonator = IQMCircuit(backend.target.num_qubits)
    circuit_with_resonator.add_bits(circuit.clbits)
    qubit_indices = [backend.qubit_name_to_index(qb) for qb in backend.physical_qubits if not qb.startswith("COMP_R")]
    circuit_with_resonator.append(
        circuit,
        [circuit_with_resonator.qubits[qubit_indices[i]] for i in range(circuit.num_qubits)],
        circuit.clbits,
    )

    # Transpile the circuit using the fake target without resonators
    simple_transpile = transpile(
        circuit_with_resonator,
        target=backend.target,
        basis_gates=backend.target.operation_names,
        **qiskit_transpiler_qwargs,
    )

    # Construct the pass sequence for the additional passes
    passes = []
    if optimize_single_qubits:
        optimize_pass = IQMOptimizeSingleQubitGates(remove_final_rzs, ignore_barriers)
        passes.append(optimize_pass)

    if "move" in backend.architecture.gates.keys():
        move_pass = IQMNaiveResonatorMoving(backend.target, backend.target.operation_names)
        passes.append(move_pass)

    #    circuit_with_resonator = add_resonators_to_circuit(simple_transpile, backend)
    # else:
    #    circuit_with_resonator = simple_transpile

    # Transpiler passes strip the layout information, so we need to add it back
    layout = simple_transpile._layout
    # TODO Update the circuit so that following passes can use the layout information,
    # old buggy logic in _add_resonators_to_circuit
    # TODO Add actual tests for the updating the layout. Currrently not done because Deneb's fake_target is
    # fully connected.
    transpiled_circuit = PassManager(passes).run(simple_transpile)
    transpiled_circuit._layout = layout
    return transpiled_circuit


def _add_resonators_to_circuit(circuit: QuantumCircuit, backend: IQMBackendBase) -> QuantumCircuit:
    """Add resonators to a circuit for a backend that supports multiple resonators.

    Args:
        circuit: The circuit to add resonators to.
        backend: The backend to add resonators for.

    Returns:
        QuantumCircuit: The circuit with resonators added.
    """
    qubit_indices = [backend.qubit_name_to_index(qb) for qb in backend.physical_qubits if not qb.startswith("COMP_R")]
    resonator_indices = [backend.qubit_name_to_index(qb) for qb in backend.physical_qubits if qb.startswith("COMP_R")]
    n_classical_regs = len(circuit.cregs)
    n_qubits = len(qubit_indices)
    n_resonators = len(resonator_indices)

    circuit_with_resonator = IQMCircuit(n_qubits + n_resonators, n_classical_regs)
    # Update and copy the initial and final layout of the circuit found by the transpiler
    layout_dict = {
        qb: i + sum(1 for r_i in resonator_indices if r_i <= i + n_resonators)
        for qb, i in circuit._layout.initial_layout._v2p.items()
    }
    layout_dict.update({Qubit(QuantumRegister(n_resonators, "resonator"), r_i): r_i for r_i in resonator_indices})
    initial_layout = Layout(input_dict=layout_dict)
    init_mapping = layout_dict
    final_layout = None
    if circuit.layout.final_layout:
        final_layout_dict = {
            qb: i + sum(1 for r_i in resonator_indices if r_i <= i + n_resonators)
            for qb, i in circuit.layout.final_layout._v2p.items()
        }
        final_layout_dict.update(
            {Qubit(QuantumRegister(n_resonators, "resonator"), r_i): r_i for r_i in resonator_indices}
        )
        final_layout = Layout(final_layout_dict)
    new_layout = TranspileLayout(initial_layout, init_mapping, final_layout=final_layout)
    circuit_with_resonator.append(circuit, circuit_with_resonator.qregs, circuit_with_resonator.cregs)
    circuit_with_resonator = circuit_with_resonator.decompose()
    circuit_with_resonator._layout = new_layout
    return circuit_with_resonator
