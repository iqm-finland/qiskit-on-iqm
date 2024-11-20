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
from functools import partial
from typing import Any, Callable, Literal, TypedDict, cast, get_type_hints
from unittest.mock import Mock
from uuid import UUID

from mockito import matchers, when
from qiskit import transpile
from qiskit.circuit import QuantumCircuit, Qubit
from qiskit.circuit.quantumcircuitdata import CircuitInstruction
from qiskit.transpiler.exceptions import TranspilerError
import requests
from requests import Response

from iqm.iqm_client import Circuit, DynamicQuantumArchitecture, GateInfo, Instruction, IQMClient
from iqm.qiskit_iqm.iqm_move_layout import generate_initial_layout
from iqm.qiskit_iqm.iqm_provider import IQMBackend


class AllowedOps(TypedDict):
    cz: list[tuple[int, int]]
    prx: list[int]
    move: list[tuple[int, int]]
    measure: list[int]


ALLOWED_OP_NAMES = get_type_hints(AllowedOps).keys()


def get_mocked_backend(architecture: DynamicQuantumArchitecture) -> tuple[IQMBackend, IQMClient]:
    """Returns an IQM backend running on a mocked IQM client that returns the given architecture."""
    when(requests).get('http://some_url/info/client-libraries', headers=matchers.ANY, timeout=matchers.ANY).thenReturn(
        get_mock_ok_response({'iqm-client': {'min': '0.0', 'max': '999.0'}})
    )
    client = IQMClient(url='http://some_url')
    when(client).get_dynamic_quantum_architecture(None).thenReturn(architecture)
    when(client).get_dynamic_quantum_architecture(architecture.calibration_set_id).thenReturn(architecture)
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
    architecture: DynamicQuantumArchitecture,
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
    transpiled_circuit = transpile(
        circuit,
        backend,
        seed_transpiler=seed_transpiler,
        optimization_level=optimization_level,
        initial_layout=initial_layout,
    )
    job = backend.run(transpiled_circuit, shots=1000)
    assert job.job_id() == '00000001-0002-0003-0004-000000000005'
    assert len(submitted_circuits_batch.all_values) == 1
    assert len(submitted_circuits_batch.value['circuits']) == 1
    return Circuit.model_validate(submitted_circuits_batch.value['circuits'][0])


def describe_instruction(instruction: Instruction) -> str:
    """Returns a string describing the instruction (includes name and locus)."""
    return f"{instruction.name}:{','.join(instruction.qubits)}"


def _get_allowed_ops(backend: IQMBackend) -> AllowedOps:
    ops_with_indices = _map_operations_to_indices(backend.architecture.gates, backend.architecture.components)
    return _coerce_to_allowed_ops(ops_with_indices)


def _map_operations_to_indices(ops: dict[str, GateInfo], components: tuple[str, ...]) -> dict[str, list[list[int]]]:
    return {
        op_name: [[components.index(q) for q in valid_operands] for valid_operands in ops[op_name].loci]
        for op_name in ALLOWED_OP_NAMES
        if op_name in ops
    }


def _coerce_to_allowed_ops(operations: dict[str, list[list[int]]]) -> AllowedOps:
    op_mapping: dict[str, Callable] = {
        'cz': partial(_tuplify, symmetric=True),  # Order of operations does not matter for CZ
        'prx': _flatten,
        'move': _tuplify,
        'measure': _flatten,
    }
    ops = {op_name: fn(operations[op_name]) if op_name in operations else [] for op_name, fn in op_mapping.items()}
    return cast(AllowedOps, ops)


def _tuplify(valid_operands: list[list[int]], symmetric: bool = False) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for operands in valid_operands:
        if len(operands) != 2:
            raise TranspilerError('Binary operation must have two operands')
        result.append((operands[0], operands[1]))
        if symmetric:
            result.append((operands[1], operands[0]))
    return result


def _flatten(operands: list[list[Any]]) -> list[Any]:
    return sum(operands, [])


def _is_valid_instruction(circuit: QuantumCircuit, allowed_ops: AllowedOps, instruction: CircuitInstruction) -> bool:
    operation_name = instruction.operation.name
    if operation_name == 'move':
        return _verify_move(circuit, allowed_ops, instruction.qubits)
    if operation_name == 'r':
        return _verify_r(circuit, allowed_ops, instruction.qubits)
    if operation_name == 'cz':
        return _verify_cz(circuit, allowed_ops, instruction.qubits)
    raise TranspilerError('Unknown operation.')


def _make_verify_instruction(
    instruction_name: Literal['cz', 'prx', 'move', 'measure'], n_operands: int
) -> Callable[[QuantumCircuit, AllowedOps, tuple[Qubit, ...]], bool]:
    def __verify(circuit: QuantumCircuit, allowed_ops: AllowedOps, qubits: tuple[Qubit, ...]) -> bool:
        if instruction_name not in allowed_ops:
            raise TranspilerError('Operation not supported.')
        allowed_operands = allowed_ops[instruction_name]
        idx = tuple(circuit.find_bit(q).index for q in qubits)
        if len(idx) != n_operands:
            raise TranspilerError('Operation got wrong number of operands.')
        return (idx[0] if len(idx) == 1 else idx) in allowed_operands

    return __verify


_verify_move = _make_verify_instruction('move', 2)
_verify_r = _make_verify_instruction('prx', 1)
_verify_cz = _make_verify_instruction('cz', 2)
