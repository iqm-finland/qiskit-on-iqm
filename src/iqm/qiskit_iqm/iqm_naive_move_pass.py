# Copyright 2024 Qiskit on IQM developers
"""Naive transpilation for N-star architecture"""

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import QuantumRegister, Qubit
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
from qiskit.transpiler import Layout, TranspileLayout
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.passmanager import PassManager

from .iqm_backend import IQMBackendBase
from .iqm_circuit import IQMCircuit
from .iqm_transpilation import IQMOptimizeSingleQubitGates
from .move_gate import MoveGate


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

    def __init__(self, resonator_register: int, move_qubits: list[int], gate_set: list[str]):
        """WIP Naive transpilation pass for resonator moving

        Args:
            resonator_register (int): Which qubit/vertex index represents the resonator.
            move_qubits (int): Which qubits (indices) can be moved into the resonator.
            gate_set (list[str]): Which gates are allowed by the target backend.
        """
        super().__init__()
        self.resonator_register = resonator_register
        self.current_resonator_state_location = resonator_register
        self.move_qubits = move_qubits
        self.gate_set = gate_set

    def run(self, dag: DAGCircuit):  # pylint: disable=too-many-branches
        """Run the IQMNaiveResonatorMoving pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to map.

        Returns:
            DAGCircuit: A mapped DAG.

        Raises:
            TranspilerError: if the layout are not compatible with the DAG, or if the input gate set is incorrect.
        """
        new_dag = dag.copy_empty_like()
        # Check for sensible inputs
        if len(dag.qregs) != 1 or dag.qregs.get("q", None) is None:
            raise TranspilerError("IQMNaiveResonatorMoving runs on physical circuits only")

        # Create a trivial layout
        canonical_register = dag.qregs["q"]
        trivial_layout = Layout.generate_trivial_layout(canonical_register)
        current_layout = trivial_layout.copy()

        for layer in dag.serial_layers():
            subdag = layer["graph"]
            if len(layer["partition"]) > 0:
                qubits = layer["partition"][0]
            else:
                new_dag.compose(subdag)
                continue  # No qubit gate (e.g. Barrier)

            if sum(subdag.count_ops().values()) > 1:
                raise TranspilerError(
                    """The DAGCircuit is not flattened enough for this transpiler pass.
                    It needs to be processed by another pass first."""
                )
            if list(subdag.count_ops().keys())[0] not in self.gate_set:
                raise TranspilerError(
                    """Encountered an incompatible gate in the DAGCircuit.
                    Please transpile to the correct gate set first."""
                )

            if len(qubits) == 1:  # Single qubit gate
                # Check if the qubit is not in the resonator
                if self.current_resonator_state_location == dag.qubits.index(qubits[0]):
                    # Unload the current qubit from the resonator
                    new_dag.compose(
                        self._move_resonator(dag.qubits.index(qubits[0]), canonical_register, current_layout)
                    )
                new_dag.compose(subdag)
            elif len(qubits) == 2:  # Two qubit gate
                physical_q0 = current_layout[qubits[0]]
                physical_q1 = current_layout[qubits[1]]
                if self.current_resonator_state_location in (physical_q0, physical_q1):
                    # The resonator is already loaded with the correct qubit data
                    pass
                else:
                    swap_layer = DAGCircuit()
                    swap_layer.add_qreg(canonical_register)
                    if self.current_resonator_state_location != self.resonator_register:
                        # Unload the current qubit from the resonator
                        new_dag.compose(
                            self._move_resonator(
                                self.current_resonator_state_location, canonical_register, current_layout
                            )
                        )
                    # Load the new qubit to the resonator
                    if physical_q0 in self.move_qubits and physical_q1 in self.move_qubits:
                        # We can choose, let's select the better one by seeing which one is used most.
                        chosen_qubit = self._lookahead_first_qubit_used(dag, subdag)
                        new_qubit_to_load = current_layout[chosen_qubit]
                    elif physical_q0 in self.move_qubits:
                        new_qubit_to_load = physical_q0
                    elif physical_q1 in self.move_qubits:
                        new_qubit_to_load = physical_q1
                    else:
                        raise TranspilerError(
                            """Two qubit gate between qubits that are not allowed to move.
                            Please route the circuit first."""
                        )
                    new_dag.compose(self._move_resonator(new_qubit_to_load, canonical_register, current_layout))
                # Add the gate to the circuit
                order = list(range(len(canonical_register)))
                order[self.resonator_register] = self.current_resonator_state_location
                order[self.current_resonator_state_location] = self.resonator_register
                new_dag.compose(subdag, qubits=order)
            else:
                raise TranspilerError(
                    """Three qubit gates are not allowed as input for this pass.
                    Please use a different transpiler pass to decompose first."""
                )

        new_dag.compose(
            self._move_resonator(
                self.current_resonator_state_location,
                canonical_register,
                current_layout,
            )
        )
        return new_dag

    def _lookahead_first_qubit_used(self, full_dag: DAGCircuit, current_layer: DAGCircuit) -> Qubit:
        """Lookahead function to see which qubit will be used first again for a CZ gate.

        Args:
            full_dag (DAGCircuit): The DAG representing the circuit
            current_layer (DAGCircuit): The DAG representing the current operator

        Returns:
            Qubit: Which qubit is recommended to move because it will be used first.
        """
        nodes = [n for n in current_layer.nodes() if isinstance(n, DAGOpNode)]
        current_opnode = nodes[0]
        qb1, qb2 = current_opnode.qargs
        next_ops = [
            n for n, _ in full_dag.bfs_successors(current_opnode) if isinstance(n, DAGOpNode) and n.name == "cz"
        ]
        # Check which qubit will be used next first
        for qb1_used, qb2_used in zip([qb1 in n.qargs for n in next_ops], [qb2 in n.qargs for n in next_ops]):
            if qb1_used and not qb2_used:
                return qb1
            if qb2_used and not qb1_used:
                return qb2
        return qb1

    def _move_resonator(self, qubit: int, canonical_register: QuantumRegister, current_layout: Layout):
        """Logic for creating the DAG for swapping a qubit in and out of the resonator.

        Args:
            qubit (int): The qubit to swap in or out. The returning DAG is empty if the qubit is the resonator.
            canonical_register (QuantumRegister): The qubit register to initialize the DAG
            current_layout (Layout): The current qubit layout to map the qubit index to a Qiskit Qubit object.

        Returns:
            DAGCircuit: A DAG storing the MoveGate logic to be added into the circuit by this TranspilerPass.
        """
        swap_layer = DAGCircuit()
        swap_layer.add_qreg(canonical_register)
        if qubit != self.resonator_register:
            swap_layer.apply_operation_back(
                MoveGate(),
                qargs=(current_layout[qubit], current_layout[self.resonator_register]),
                cargs=(),
                check=False,
            )
            if self.current_resonator_state_location == self.resonator_register:
                # We just loaded the qubit into the register
                self.current_resonator_state_location = qubit
            else:
                # We just unloaded the qubit from the register
                self.current_resonator_state_location = self.resonator_register
        return swap_layer


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
    circuit_with_resonator = IQMCircuit(backend.fake_target.num_qubits)
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
        target=backend.fake_target,
        basis_gates=backend.fake_target.operation_names,
        **qiskit_transpiler_qwargs,
    )

    # Construct the pass sequence for the additional passes
    passes = []
    if optimize_single_qubits:
        optimize_pass = IQMOptimizeSingleQubitGates(remove_final_rzs, ignore_barriers)
        passes.append(optimize_pass)

    if "move" in backend.architecture.operations.keys():
        move_pass = IQMNaiveResonatorMoving(
            backend.architecture.qubits.index("COMP_R"),
            [backend.qubit_name_to_index(q) for q, r in backend.architecture.operations["move"] if r == "COMP_R"],
            backend._physical_target.operation_names,
        )
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
