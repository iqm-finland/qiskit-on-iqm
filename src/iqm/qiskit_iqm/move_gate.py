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
"""Move gate to be used with Qiskit Quantum Circuits."""

from qiskit.circuit import Gate
from qiskit.circuit.library import CXGate
from qiskit.circuit.quantumcircuit import QuantumCircuit, QuantumRegister


class MoveGate(Gate):
    r"""The MOVE operation is a unitary population exchange operation between a qubit and a resonator.
    Its effect is only defined in the invariant subspace :math:`S = \text{span}\{|00\rangle, |01\rangle, |10\rangle\}`,
    where it swaps the populations of the states :math:`|01\rangle` and :math:`|10\rangle`.
    Its effect on the orthogonal subspace is undefined.

    MOVE has the following presentation in the subspace :math:`S`:

    .. math:: \text{MOVE}_S = |00\rangle \langle 00| + a |10\rangle \langle 01| + a^{-1} |01\rangle \langle 10|,

    where :math:`a` is an undefined complex phase that is canceled when the MOVE gate is applied a second time.

    To ensure that the state of the qubit and resonator has no overlap with :math:`|11\rangle`, it is
    recommended that no single qubit gates are applied to the qubit in between a
    pair of MOVE operations.

    Note: At this point the locus for the move gate must be defined in the order: ``[qubit, resonator]``.
    """

    def __init__(self, label=None):
        """Initializes the move gate"""
        super().__init__("move", 2, [], label=label)

    def _define(self):
        """Pretend that this gate is an SWAP for the purpose of matrix checking.

        The |0> needs to be traced out for the resonator 'qubits'.

        gate swap a,b {
            cx q[0],q[1];
            cx q[1],q[0];
            cx q[0],q[1];
        }
        """

        q = QuantumRegister(2, "q")
        qc = QuantumCircuit(q, name=self.name)
        rules = [(CXGate(), [q[0], q[1]], []), (CXGate(), [q[1], q[0]], []), (CXGate(), [q[0], q[1]], [])]
        for instr, qargs, cargs in rules:
            qc._append(instr, qargs, cargs)

        self.definition = qc
