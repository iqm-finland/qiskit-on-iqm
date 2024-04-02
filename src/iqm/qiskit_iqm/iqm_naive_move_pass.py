# Copyright 2024 Qiskit on IQM developers
"""Naive transpilation for N-star architecture"""

from datetime import datetime
from typing import Optional, Union

from qiskit import QuantumCircuit, user_config
from qiskit.circuit import QuantumRegister, Qubit
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
from qiskit.providers.models import BackendProperties
from qiskit.transpiler import CouplingMap, Layout, TranspileLayout
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.target import Target

from .fake_backends.iqm_fake_backend import IQMFakeBackend
from .iqm_circuit import IQMCircuit
from .iqm_provider import IQMBackend
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
                if self.current_resonator_state_location == qubits[0].index:
                    # Unload the current qubit from the resonator
                    new_dag.compose(self._move_resonator(qubits[0].index, canonical_register, current_layout))
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


def _to_qubit_indices(backend: Union[IQMBackend, IQMFakeBackend], qubit_names: list[str]) -> list[int]:
    indices = [backend.qubit_name_to_index(res) for res in qubit_names]
    return [i for i in indices if i is not None]


def _qubit_to_index_without_resonator(
    backend: Union[IQMBackend, IQMFakeBackend], resonator_registers: list[str], qb: str
) -> Optional[int]:
    resonator_indices = _to_qubit_indices(backend, resonator_registers)
    idx = backend.qubit_name_to_index(qb)
    return (idx - sum(1 for r in resonator_indices if r < idx)) if idx is not None else None


def _generate_coupling_map_without_resonator(backend: Union[IQMBackend, IQMFakeBackend]) -> CouplingMap:
    # Grab qubits from backend operations
    allowed_ops = backend.architecture.operations
    allowed_czs = allowed_ops["cz"]
    allowed_moves = allowed_ops["move"]

    iqm_registers = backend.architecture.qubits
    resonator_registers = [r for r in iqm_registers if r.startswith("COMP_R")]

    move_qubits = {r: [q for pair in allowed_moves for q in pair if r in pair and q != r] for r in resonator_registers}

    edges = []
    for qb1, qb2 in allowed_czs:
        if qb1 in resonator_registers:
            vs1 = move_qubits[qb1]
        else:
            vs1 = [qb1]
        if qb2 in resonator_registers:
            vs2 = move_qubits[qb2]
        else:
            vs2 = [qb2]
        for v1 in vs1:
            for v2 in vs2:
                qb1_idx = _qubit_to_index_without_resonator(backend, resonator_registers, v1)
                qb2_idx = _qubit_to_index_without_resonator(backend, resonator_registers, v2)
                if qb1_idx is not None and qb2_idx is not None:
                    edges.append((qb1_idx, qb2_idx))

    return CouplingMap(edges)


def build_IQM_star_pass_manager_config(
    backend: Union[IQMBackend, IQMFakeBackend], circuit: QuantumCircuit
) -> PassManagerConfig:
    """Build configuration for IQM backend.

    We need to pass precomputed values to be used in transpiler passes via backend_properties.
    This function performs precomputation for the backend and packages the values to the config object."""
    coupling_map = _generate_coupling_map_without_resonator(backend)
    allowed_ops = backend.architecture.operations
    allowed_moves = allowed_ops["move"]

    iqm_registers = backend.architecture.qubits
    classical_registers = [bit.index for bit in circuit.clbits]
    resonator_registers = [r for r in iqm_registers if r.startswith("COMP_R")]
    move_qubits = {r: [q for pair in allowed_moves for q in pair if r in pair and q != r] for r in resonator_registers}
    qubit_registers = [q for q in iqm_registers if q not in resonator_registers]

    qubit_indices = [backend.qubit_name_to_index(qb) for qb in qubit_registers]
    bit_indices = [_qubit_to_index_without_resonator(backend, resonator_registers, qb) for qb in qubit_registers]

    resonator_indices = [backend.qubit_name_to_index(r) for r in resonator_registers]

    if len(resonator_indices) != 1:
        raise NotImplementedError("Device must have exactly one resonator.")
    if any(idx is None for idx in resonator_indices):
        raise RuntimeError("Could not find index of a resonator.")
    move_indices = _to_qubit_indices(backend, move_qubits[resonator_registers[0]])

    extra_backend_properties = {
        "resonator_indices": resonator_indices,
        "move_indices": move_indices,
        "qubit_indices": qubit_indices,
        "bit_indices": bit_indices,
        "classical_registers": classical_registers,
    }
    backend_properties = BackendProperties(
        backend_name=backend.name,
        backend_version="",
        last_update_date=datetime.now(),
        qubits=[],
        gates=[],
        general=[],
    )
    backend_properties._data.update(**extra_backend_properties)
    return PassManagerConfig(
        basis_gates=backend.operation_names,
        backend_properties=backend_properties,
        target=Target(num_qubits=len(qubit_indices)),
        coupling_map=coupling_map,
    )


def build_IQM_star_pass(pass_manager_config: PassManagerConfig) -> TransformationPass:
    """Build translate pass for IQM star architecture"""

    backend_props = pass_manager_config.backend_properties.to_dict()
    resonator_indices = backend_props.get("resonator_indices")
    return IQMNaiveResonatorMoving(
        resonator_indices[0],
        backend_props.get("move_indices"),
        pass_manager_config.basis_gates,
    )


def transpile_to_IQM(  # pylint: disable=too-many-arguments
    circuit: QuantumCircuit,
    backend: Union[IQMBackend, IQMFakeBackend],
    optimize_single_qubits: bool = True,
    ignore_barriers: bool = False,
    remove_final_rzs: bool = False,
    optimization_level: Optional[int] = None,
) -> QuantumCircuit:
    """Basic function for transpiling to IQM backends. Currently works with Deneb and Garnet

    Args:
        circuit (QuantumCircuit): The circuit to be transpiled without MOVE gates.
        backend (IQMBackend | IQMFakeBackend): The target backend to compile to containing a single resonator.
        optimize_single_qubits (bool): Whether to optimize single qubit gates away (default = True).
        ignore_barriers (bool): Whether to ignore barriers when optimizing single qubit gates away (default = False).
        remove_final_rzs (bool): Whether to remove the final Rz rotations (default = False).
        optimization_level: How much optimization to perform on the circuits as per Qiskit transpiler.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation time.

            * 0: no optimization
            * 1: light optimization (default)
            * 2: heavy optimization
            * 3: even heavier optimization

    Raises:
        NotImplementedError: Thrown when the backend supports multiple resonators.

    Returns:
        QuantumCircuit: The transpiled circuit ready for running on the backend.
    """

    passes = []
    if optimize_single_qubits:
        optimize_pass = IQMOptimizeSingleQubitGates(remove_final_rzs, ignore_barriers)
        passes.append(optimize_pass)

    if optimization_level is None:
        config = user_config.get_config()
        optimization_level = config.get("transpile_optimization_level", 1)

    if "move" not in backend.architecture.operations.keys():
        pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
        simple_transpile = pass_manager.run(circuit)
        if passes:
            return PassManager(passes).run(simple_transpile)
        return simple_transpile
    pass_manager_config = build_IQM_star_pass_manager_config(backend, circuit)
    move_pass = build_IQM_star_pass(pass_manager_config)
    passes.append(move_pass)

    backend_props = pass_manager_config.backend_properties.to_dict()
    qubit_indices = backend_props.get("qubit_indices")
    resonator_indices = backend_props.get("resonator_indices")
    classical_registers = backend_props.get("classical_registers")
    n_qubits = len(qubit_indices)
    n_resonators = len(resonator_indices)

    pass_manager = generate_preset_pass_manager(
        optimization_level,
        basis_gates=pass_manager_config.basis_gates,
        coupling_map=pass_manager_config.coupling_map,
    )
    simple_transpile = pass_manager.run(circuit)
    circuit_with_resonator = IQMCircuit(
        n_qubits + n_resonators,
        max(classical_registers) + 1 if len(classical_registers) > 0 else 0,
    )

    layout_dict = {
        qb: i + sum(1 for r_i in resonator_indices if r_i <= i + n_resonators)
        for qb, i in simple_transpile._layout.initial_layout._v2p.items()
    }
    layout_dict.update({Qubit(QuantumRegister(n_resonators, "resonator"), r_i): r_i for r_i in resonator_indices})
    initial_layout = Layout(input_dict=layout_dict)
    init_mapping = layout_dict
    final_layout = None
    if simple_transpile.layout.final_layout:
        final_layout_dict = {
            qb: i + sum(1 for r_i in resonator_indices if r_i <= i + n_resonators)
            for qb, i in simple_transpile.layout.final_layout._v2p.items()
        }
        final_layout_dict.update(
            {Qubit(QuantumRegister(n_resonators, "resonator"), r_i): r_i for r_i in resonator_indices}
        )
        final_layout = Layout(final_layout_dict)
    new_layout = TranspileLayout(initial_layout, init_mapping, final_layout=final_layout)

    circuit_with_resonator.append(
        simple_transpile, qubit_indices, classical_registers if len(classical_registers) > 0 else None
    )
    circuit_with_resonator._layout = new_layout
    circuit_with_resonator = circuit_with_resonator.decompose()

    transpiled_circuit = PassManager(passes).run(circuit_with_resonator)
    transpiled_circuit._layout = new_layout
    return transpiled_circuit
