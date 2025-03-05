# Copyright 2023 Qiskit on IQM developers
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
"""Transpilation tool to optimize the decomposition of single-qubit gates tailored to IQM hardware."""
import math
import warnings

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.circuit.library import RGate, UnitaryGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes import BasisTranslator, Optimize1qGatesDecomposition, RemoveBarriers
from qiskit.transpiler.passmanager import PassManager

TOLERANCE = 1e-10  # The tolerance for equivalence checking against zero.


class IQMOptimizeSingleQubitGates(TransformationPass):
    r"""Optimize the decomposition of single-qubit gates for the IQM gate set.

    This optimization pass expects the circuit to be correctly layouted and translated to the IQM architecture
    and raises an error otherwise.
    The optimization logic follows the steps:

    1. Convert single-qubit gates to :math:`U` gates and combine all neighboring :math:`U` gates.
    2. Convert :math:`U` gates according to
       :math:`U(\theta , \phi , \lambda) = ~ RZ(\phi + \lambda) R(\theta, \pi / 2  - \lambda)`.
    3. Commute `RZ` gates to the end of the circuit using the fact that `RZ` and `CZ` gates commute, and
       :math:`R(\theta , \phi) RZ(\lambda) = RZ(\lambda) R(\theta, \phi - \lambda)`.
    4. Drop `RZ` gates immediately before measurements, and otherwise replace them according to
       :math:`RZ(\lambda) = R(\pi, \lambda / 2) R(- \pi, 0)`.

    Args:
        drop_final_rz: Drop terminal RZ gates even if there are no measurements following them (since they do not affect
            the measurement results). Note that this will change the unitary propagator of the circuit.
            It is recommended always to set this to true as the final RZ gates do no change the measurement outcomes of
            the circuit.
        ignore_barriers (bool): Removes the barriers from the circuit before optimization (default = False).
    """

    def __init__(self, drop_final_rz: bool = True, ignore_barriers: bool = False):
        super().__init__()
        self._basis = ['r', 'cz', 'move']
        self._intermediate_basis = ['u', 'cz', 'move']
        self._drop_final_rz = drop_final_rz
        self._ignore_barriers = ignore_barriers

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        # pylint: disable=too-many-branches
        self._validate_ops(dag)
        # accumulated RZ angles for each qubit, from the beginning of the circuit to the current gate
        rz_angles: list[float] = [0] * dag.num_qubits()

        if self._ignore_barriers:
            dag = RemoveBarriers().run(dag)
        # convert all gates in the circuit to U and CZ gates
        dag = BasisTranslator(SessionEquivalenceLibrary, self._intermediate_basis).run(dag)
        # combine all sequential U gates into one
        dag = Optimize1qGatesDecomposition(self._intermediate_basis).run(dag)
        for node in dag.topological_op_nodes():
            if node.name == 'u':
                # convert into PRX + RZ
                qubit_index = dag.find_bit(node.qargs[0])[0]
                if math.isclose(node.op.params[0], 0, abs_tol=TOLERANCE):
                    dag.remove_op_node(node)
                else:
                    dag.substitute_node(
                        node, RGate(node.op.params[0], np.pi / 2 - node.op.params[2] - rz_angles[qubit_index])
                    )
                phase = node.op.params[1] + node.op.params[2]
                dag.global_phase += phase / 2
                rz_angles[qubit_index] += phase
            elif node.name in {'measure', 'reset'}:
                # measure and reset destroy phase information. The local phases before and after such
                # an operation are in principle independent, and the local computational frame phases
                # are arbitrary so we could set rz_angles to any values here, but zeroing the
                # angles results in fewest changes to the circuit.
                for qubit in node.qargs:
                    rz_angles[dag.find_bit(qubit)[0]] = 0
            elif node.name == 'barrier':
                # TODO barriers are meant to restrict circuit optimization, so strictly speaking
                # we should output any accumulated ``rz_angles`` here as explicit z rotations (like
                # the final rz:s). However, ``rz_angles`` simply represents a choice of phases for the
                # local computational frames for the rest of the circuit (the initial part has already
                # been transformed). This choice of local phases is in principle arbitrary, so maybe it
                # makes no sense to convert it into active z rotations if we hit a barrier?
                pass
            elif node.name == 'move':
                # acts like iSWAP with RZ, moving it to the other component
                qb, res = dag.find_bit(node.qargs[0])[0], dag.find_bit(node.qargs[1])[0]
                rz_angles[res], rz_angles[qb] = rz_angles[qb], rz_angles[res]
            elif node.name in {'cz', 'delay'}:
                pass  # commutes with RZ gates
            else:
                raise ValueError(
                    f"Unexpected operation '{node.name}' in circuit given to IQMOptimizeSingleQubitGates pass"
                )

        if not self._drop_final_rz:
            for qubit_index, rz_angle in enumerate(rz_angles):
                if rz_angle != 0:
                    qubit = dag.qubits[qubit_index]
                    dag.apply_operation_back(RGate(-np.pi, 0), qargs=(qubit,))
                    dag.apply_operation_back(RGate(np.pi, rz_angles[qubit_index] / 2), qargs=(qubit,))

        return dag

    def _validate_ops(self, dag: DAGCircuit):
        valid_ops = self._basis + ['measure', 'reset', 'delay', 'barrier']
        for node in dag.op_nodes():
            if node.name not in valid_ops:
                raise ValueError(
                    f'Invalid operation \'{node.name}\' found in IQMOptimize1QbDecomposition pass, '
                    + f'expected operations {valid_ops}'
                )


def optimize_single_qubit_gates(
    circuit: QuantumCircuit, drop_final_rz: bool = True, ignore_barriers: bool = False
) -> QuantumCircuit:
    """Optimize number of single-qubit gates in a transpiled circuit exploiting the IQM specific gate set.

    Args:
        circuit: quantum circuit to optimize
        drop_final_rz: Drop terminal RZ gates even if there are no measurements following them (since they do not affect
            the measurement results). Note that this will change the unitary propagator of the circuit.
            It is recommended always to set this to true as the final RZ gates do no change the measurement outcomes of
            the circuit.
        ignore_barriers (bool): Removes barriers from the circuit if they exist (default = False) before optimization.

    Returns:
        optimized circuit
    """
    warnings.warn(
        DeprecationWarning(
            'This function is deprecated and will be removed in a later version of `iqm.qiskit_iqm`. '
            + 'Single qubit gate optimization is now automatically applied when running `qiskit.transpile()` on any '
            + 'IQM device. If you want to have more fine grained control over the optimization, please use the '
            + '`iqm.qiskit_iqm.transpile_to_IQM` function.'
        )
    )
    # Code not updated to use transpile_to_IQM due to circular imports
    new_circuit = PassManager(IQMOptimizeSingleQubitGates(drop_final_rz, ignore_barriers)).run(circuit)
    new_circuit._layout = circuit.layout
    return new_circuit


class IQMReplaceGateWithUnitaryPass(TransformationPass):
    """Transpiler pass that replaces all gates with given name in a circuit with a UnitaryGate.

    Args:
        gate: The name of the gate to replace.
        unitary: The unitary matrix to replace the gate with.
    """

    def __init__(self, gate: str, unitary: list[list[float]]):
        super().__init__()
        self.gate = gate
        self.unitary = unitary

    def run(self, dag):
        for node in dag.op_nodes():
            if node.name == self.gate:
                dag.substitute_node(node, UnitaryGate(self.unitary))
        return dag
