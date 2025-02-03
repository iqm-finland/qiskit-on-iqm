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
"""MOVE gate to be used on the IQM Star architecture."""
import numpy as np
from qiskit.circuit import Gate
import qiskit.quantum_info as qi

# MOVE gate has undefined phases, so we pick two arbitrary phases here
_phase_1 = np.exp(0.7j)
_phase_2 = 1.0  # np.exp(1.2j)
MOVE_GATE_UNITARY = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, _phase_1, 0.0],
    [0.0, _phase_1.conj(), 0.0, 0.0],
    [0.0, 0.0, 0.0, _phase_2],
]
"""Unitary matrix for simulating the ideal MOVE gate.

This matrix is not a realistic description of MOVE, since it applies a zero phase on the moved
state, and acts as identity in the :math:`|11\rangle` subspace, thus being equal to the SWAP gate."""


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

    .. note::
       The MOVE gate must always be be applied on the qubit and the resonator in the
       order ``[qubit, resonator]``, regardless of which component is currently holding the state.
    """

    def __init__(self, label=None):
        """Initializes the move gate"""
        super().__init__("move", 2, [], label=label)
        self.unitary = qi.Operator(MOVE_GATE_UNITARY)

    def _define(self):
        """This function is purposefully not defined so that that the Qiskit transpiler cannot accidentally
        decompose the MOVE gate into a sequence of other gates, instead it will throw an error.
        """
        return
