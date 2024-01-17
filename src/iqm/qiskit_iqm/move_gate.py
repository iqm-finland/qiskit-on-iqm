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
"""Move gate to be used with Qiskit Quantum Circuits"""

from qiskit.circuit import Gate


class MoveGate(Gate):
    """Custom gate that can be used to model the move gate in a quantum circuit"""

    def __init__(self, label=None):
        """Initializes the move gate"""
        super().__init__("move", 2, [], label=label)
