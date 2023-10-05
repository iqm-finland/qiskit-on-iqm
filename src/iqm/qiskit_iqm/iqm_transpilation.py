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
"""Transpilation tool to optimize the decomposition of 1 qubit gates tailored to IQM hardware."""
import copy

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Qubit
from qiskit.circuit.library import RGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes import Optimize1qGatesDecomposition, Unroller
from qiskit.transpiler.passmanager import PassManager


class IQMOptimize1QbDecomposition(TransformationPass):
    r"""Optimize the decomposition of 1 qubit gates for the IQM gate set.

    This optimisation pass expects the circuit to be correctly layouted and translated to the IQM architecture
    and raises an error otherwise.
    The optimisation logic follows the following steps:

    1. Convert single qubit gates to :math:`U` gates and combine all neighbouring :math:`U` gates.
    2. Convert :math:`U` gates according to
       :math:`U(\theta , \phi , \lambda) ~ RZ(\phi + \lambda) R(\theta, \pi / 2  - \lambda)`.
    3. Commute `RZ` gates to the end of the circuit using the fact that `RZ` and `CZ` gates commute, and
       :math:`R(\theta , \phi) RZ(\lambda) = RZ(\lambda) R(\theta, \phi - \lambda)`.
    4. Drop `RZ` gates immediately before measurements, and otherwise replace them according to
       :math:`RZ(\lambda) = R(\pi, \lambda / 2) R(- \pi, 0)`.
    """

    def __init__(self):
        super().__init__()
        self._basis = ['r', 'cz']
        self._intermediate_basis = ['u', 'cz']

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        self._validate_ops(dag)
        # accumulated RZ angles for each qubit, from the beginning of the circuit to the current gate
        rz_angles: list[float] = [0] * dag.num_qubits()
        # convert all gates in the circuit to U and CZ gates
        dag = Unroller(self._intermediate_basis).run(dag)
        # combine all sequential U gates into one
        dag = Optimize1qGatesDecomposition(self._intermediate_basis).run(dag)
        last_op_is_measurement: dict[Qubit, bool] = {qubit: False for qubit in dag.qubits}
        for node in dag.topological_op_nodes():
            if node.name == 'u':
                qubit_index = dag.find_bit(node.qargs[0])[0]
                dag.substitute_node(
                    node, RGate(node.op.params[0], np.pi / 2 - node.op.params[2] - rz_angles[qubit_index])
                )
                phase = node.op.params[1] + node.op.params[2]
                dag.global_phase += phase / 2
                rz_angles[qubit_index] += phase
            if node.name == 'measure':
                for qubit in node.qargs:
                    last_op_is_measurement[qubit] = True
            else:
                for qubit in node.qargs:
                    last_op_is_measurement[qubit] = False

        for qubit, has_terminal_measurement in last_op_is_measurement.items():
            qubit_index = dag.find_bit(qubit)[0]
            if not has_terminal_measurement and rz_angles[qubit_index] != 0:
                dag.apply_operation_back(RGate(-np.pi, 0), qargs=(qubit,))
                dag.apply_operation_back(RGate(np.pi, rz_angles[qubit_index] / 2), qargs=(qubit,))

        return dag

    def _validate_ops(self, dag: DAGCircuit):
        for node in dag.op_nodes():
            if node.name not in self._basis + ['measure', 'barrier']:
                raise ValueError(
                    f"""Invalid operation '{node.name}' found in IQMOptimize1QbDecomposition pass, 
                    expected operations {self._basis + ['measure', 'barrier']}"""
                )


def optimize_1_qb_gate_decomposition(circuit: QuantumCircuit) -> QuantumCircuit:
    """Optimize number of single qubit gates in a transpiled circuit exploiting the IQM specific gate set.

    Args:
        circuit: quantum circuit to optimise

    Returns:
        optimised circuit
    """
    return PassManager(IQMOptimize1QbDecomposition()).run(copy.deepcopy(circuit))
