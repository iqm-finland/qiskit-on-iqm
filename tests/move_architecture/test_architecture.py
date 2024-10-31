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
"""Testing extended quantum architecture specification.
"""
from typing import Union

from qiskit.circuit import Instruction

from tests.utils import get_mocked_backend


def test_backend_configuration_new(move_architecture):
    """Check that the extended architecture is configured correctly to the Qiskit backend."""
    assert move_architecture is not None
    backend, _client = get_mocked_backend(move_architecture)
    assert backend.target.physical_qubits == [0, 1, 2, 3, 4, 5, 6]
    assert set(backend.target.operation_names) == {'r', 'id', 'cz', 'measure', 'move'}
    assert [f'{o.name}:{o.num_qubits}' for o in backend.target.operations] == [
        'measure:1',
        'id:1',
        'r:1',
        'cz:2',
        'move:2',
    ]
    check_instruction(backend.instructions, 'r', [(1,), (2,), (3,), (4,), (5,), (6,)])
    check_instruction(backend.instructions, 'measure', [(1,), (2,), (3,), (4,), (5,), (6,)])
    check_instruction(backend.instructions, 'id', [(0,), (1,), (2,), (3,), (4,), (5,), (6,)])
    check_instruction(
        backend.instructions, 'cz', [(1, 0), (0, 1), (2, 0), (0, 2), (3, 0), (0, 3), (4, 0), (0, 4), (5, 0), (0, 5)]
    )
    check_instruction(backend.instructions, 'move', [(6, 0)])


def test_backend_configuration_adonis(adonis_architecture):
    """ "Check that the Qiskit backend configuration still works properly for Adonis architecture."""
    assert adonis_architecture is not None
    backend, _client = get_mocked_backend(adonis_architecture)
    assert backend.target.physical_qubits == [0, 1, 2, 3, 4]
    assert set(backend.target.operation_names) == {'r', 'id', 'cz', 'measure', 'reset'}
    assert [f'{o.name}:{o.num_qubits}' for o in backend.target.operations] == [
        'measure:1',
        'id:1',
        'r:1',
        'cz:2',
        'reset:1',
    ]
    check_instruction(backend.instructions, 'r', [(0,), (1,), (2,), (3,), (4,)])
    check_instruction(backend.instructions, 'measure', [(0,), (1,), (2,), (3,), (4,)])
    check_instruction(backend.instructions, 'id', [(0,), (1,), (2,), (3,), (4,)])
    check_instruction(backend.instructions, 'cz', [(0, 2), (2, 0), (1, 2), (2, 1), (3, 2), (2, 3), (4, 2), (2, 4)])


def check_instruction(
    instructions: list[tuple[Instruction, tuple[int]]],
    name: str,
    expected_connections: list[Union[tuple[int], tuple[int, int]]],
):
    """Checks that the given instruction is defined for the expected qubits (directed)."""
    target_qubits = [k for (i, k) in instructions if i.name == name]
    assert target_qubits == expected_connections
