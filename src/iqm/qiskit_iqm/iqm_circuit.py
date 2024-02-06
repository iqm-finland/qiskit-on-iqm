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
"""A simple extension of the QuantumCircuit class to allow the MOVE
gate to be applied with a .move(qubit, resonator) shortcut."""

from qiskit import QuantumCircuit

from iqm.qiskit_iqm.move_gate import MoveGate


class IQMCircuit(QuantumCircuit):
    """Extends the QuantumCircuit class, adding a shortcut for applying the MOVE gate."""

    def move(self, qubit: int, resonator: int):
        """Applies the MOVE gate to the circuit.

        Note: at this point the circuit layout is only guaranteed to work if the order
        of the qubit and the resonator is correct (qubit first, resonator second).

        Args:
            qubit: the logical index of the qubit
            resonator: the logical index of the resonator
        """
        self.append(MoveGate(), [qubit, resonator])
