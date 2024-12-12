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
"""Helper functions for circuit validation."""

from typing import Optional

from qiskit import QuantumCircuit

from iqm.iqm_client import Circuit as IQMClientCircuit
from iqm.iqm_client import IQMClient, MoveGateValidationMode
from iqm.qiskit_iqm.iqm_backend import IQMBackendBase
from iqm.qiskit_iqm.qiskit_to_iqm import serialize_instructions


def validate_circuit(
    circuit: QuantumCircuit,
    backend: IQMBackendBase,
    validate_moves: Optional[MoveGateValidationMode] = None,
    qubit_mapping: Optional[dict[int, str]] = None,
):
    """Validate a circuit against the backend."""
    if qubit_mapping is None:
        qubit_mapping = backend._idx_to_qb
    new_circuit = IQMClientCircuit(
        name="Validation circuit",
        instructions=serialize_instructions(circuit=circuit, qubit_index_to_name=qubit_mapping),
    )
    if validate_moves is None:
        validate_moves = MoveGateValidationMode.STRICT
    IQMClient._validate_circuit_instructions(
        architecture=backend.architecture,
        circuits=[new_circuit],
        validate_moves=validate_moves,
    )
