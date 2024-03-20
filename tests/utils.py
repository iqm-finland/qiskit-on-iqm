# Copyright 2022-2024 Qiskit on IQM developers
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
"""Testing and mocking utility functions.
"""
from unittest.mock import Mock
from uuid import UUID

from mockito import matchers, when
from qiskit import QuantumCircuit, execute
import requests
from requests import Response

from iqm.iqm_client import Circuit, Instruction, IQMClient, QuantumArchitectureSpecification
from iqm.qiskit_iqm.iqm_move_layout import generate_initial_layout
from iqm.qiskit_iqm.iqm_provider import IQMBackend


def get_mocked_backend(
    architecture: QuantumArchitectureSpecification,
) -> tuple[IQMBackend, IQMClient]:
    """Returns an IQM backend running on a mocked IQM client that returns the given architecture."""
    client = IQMClient(url='http://localhost')
    when(client).get_quantum_architecture().thenReturn(architecture)
    backend = IQMBackend(client)
    return backend, client


def capture_submitted_circuits(job_id: UUID = UUID('00000001-0002-0003-0004-000000000005')):
    """Mocks the given client to capture circuits that are run against it.

    Returns:
        a mockito captor that can be used to access the circuit submitted to the client.
    """
    submitted_circuits = matchers.captor()
    when(requests).post(
        matchers.ANY,
        json=submitted_circuits,
        headers=matchers.ANY,
        timeout=matchers.ANY,
    ).thenReturn(get_mock_ok_response({'id': str(job_id)}))
    return submitted_circuits


def get_mock_ok_response(json: dict) -> Response:
    """Constructs a mock response for use with mocking the requests library.

    Args:
        json - the mocked response (JSON)

    Returns:
        the mocked response class
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.history = []
    mock_response.json.return_value = json
    return mock_response


# pylint: disable=too-many-arguments
def get_transpiled_circuit_json(
    circuit: QuantumCircuit,
    architecture: QuantumArchitectureSpecification,
    seed_transpiler=None,
    optimization_level=None,
    create_move_layout: bool = False,
    initial_layout=None,
) -> Circuit:
    """Configures an IQM backend running against the given architecture, submits
    the given circuit to it, captures the transpiled circuit and returns it.

    Returns:
        the circuit that was transpiled by the IQM backend
    """
    backend, _client = get_mocked_backend(architecture)
    submitted_circuits_batch = capture_submitted_circuits()

    if create_move_layout:
        initial_layout = generate_initial_layout(backend, circuit)
    job = execute(
        circuit,
        backend,
        shots=1000,
        seed_transpiler=seed_transpiler,
        optimization_level=optimization_level,
        initial_layout=initial_layout,
    )
    assert job.job_id() == '00000001-0002-0003-0004-000000000005'
    assert len(submitted_circuits_batch.all_values) == 1
    assert len(submitted_circuits_batch.value['circuits']) == 1
    return Circuit.model_validate(submitted_circuits_batch.value['circuits'][0])


def describe_instruction(instruction: Instruction) -> str:
    """Returns a string describing the instruction (includes name and locus)."""
    return f"{instruction.name}:{','.join(instruction.qubits)}"
