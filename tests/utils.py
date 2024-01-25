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
from uuid import UUID

from mockito import matchers, mock, when
from qiskit import QuantumCircuit, execute

from iqm.iqm_client import Circuit, Instruction, IQMClient, QuantumArchitectureSpecification
from iqm.qiskit_iqm import IQMBackend
from iqm.qiskit_iqm.iqm_move_layout import generate_initial_layout


def get_mocked_backend(
    architecture: QuantumArchitectureSpecification,
) -> tuple[IQMBackend, IQMClient]:
    """Returns an IQM backend running on a mocked IQM client that returns the given architecture."""
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(architecture)
    backend = IQMBackend(client)
    return backend, client


def capture_submitted_circuits(client: IQMClient, job_id: UUID = UUID('00000001-0002-0003-0004-000000000005')):
    """Mocks the given client to capture circuits that are run against it.

    Returns:
        a mockito captor that can be used to access the circuit submitted to the client.
    """
    submitted_circuits = matchers.captor()
    when(client).submit_circuits(
        submitted_circuits,
        qubit_mapping=matchers.ANY,
        calibration_set_id=matchers.ANY,
        shots=matchers.ANY,
        circuit_duration_check=matchers.ANY,
        heralding_mode=matchers.ANY,
    ).thenReturn(job_id)
    return submitted_circuits


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
    backend, client = get_mocked_backend(architecture)
    submitted_circuits_batch = capture_submitted_circuits(client)

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
    assert len(submitted_circuits_batch.value) == 1
    return submitted_circuits_batch.value[0]


def describe_instruction(instruction: Instruction) -> str:
    """Returns a string describing the instruction (includes name and locus)."""
    return f"{instruction.name}:{','.join(instruction.qubits)}"
