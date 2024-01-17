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


def get_mocked_backend(
    architecture: QuantumArchitectureSpecification,
) -> tuple[IQMBackend, IQMClient]:
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(architecture)
    backend = IQMBackend(client)
    return backend, client


def capture_submitted_circuits(client: IQMClient, job_id: UUID = UUID('00000001-0002-0003-0004-000000000005')):
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


def get_transpiled_circuit_json(
    circuit: QuantumCircuit,
    architecture: QuantumArchitectureSpecification,
    seed_transpiler=None,
    optimization_level=None,
) -> Circuit:
    backend, client = get_mocked_backend(architecture)
    submitted_circuits_batch = capture_submitted_circuits(client)

    job = execute(circuit, backend, shots=1000, seed_transpiler=seed_transpiler, optimization_level=optimization_level)
    assert job.job_id() == '00000001-0002-0003-0004-000000000005'
    assert len(submitted_circuits_batch.all_values) == 1
    assert len(submitted_circuits_batch.value) == 1
    return submitted_circuits_batch.value[0]


def describe_instruction(instruction: Instruction) -> str:
    return f"{instruction.name}:{','.join(instruction.qubits)}"
