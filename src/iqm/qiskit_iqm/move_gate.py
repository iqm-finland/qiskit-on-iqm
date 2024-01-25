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


class MoveGate(Gate):
    r"""The MOVE operation is an operation between a qubit and resonator than moves the
    1 state between the qubit and resonator. Specifically, it transforms 01 to 10
    and 10 to 01, where indexes are ordered qubit then resonator. However, the MOVE
    operation is not defined when both the resonator and qubit are in the 1 state;
    it is not defined on the 11 state. If the MOVE operation is applied to the
    11 state there will be substantial (roughly 63%) leakage into the 02 state.
    With 11 input undefined, the matrix form of the MOVE operation is:

    .. math::

        MOVE\ q, r =
            \begin{bmatrix}
                1 & 0 & 0 & n/a \\
                0 & 0 & 1 & n/a \\
                0 & 1 & 0 & n/a \\
                0 & 0 & 0 & n/a
            \end{bmatrix}

    Due to technical limitations, the MOVE operation must be defined with the
    qubit as the first operator and the resonator as the second.

    To ensure that both the qubit and resonator are not both in the 1 state, it is
    recommended that no single qubit gates are applied to the qubit in between a
    pair of MOVE operations.
    """

    def __init__(self, label=None):
        """Initializes the move gate"""
        super().__init__("move", 2, [], label=label)
