# Copyright 2022 Qiskit on IQM developers
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
from qiskit_iqm_provider.iqm_operation_mapping import map_operation
from iqm_client import iqm_client
import qiskit


def serialize_circuit(circuit: qiskit.QuantumCircuit) -> iqm_client.Circuit:
    """Serializes a quantum circuit into the IQM data transfer format.

    Args:
        circuit: quantum circuit to serialize

    Returns:
        data transfer object representing the circuit
    """
    instructions = list(map(map_operation, circuit))
    return iqm_client.Circuit(
        name='Serialized from Cirq',
        instructions=instructions
    )

