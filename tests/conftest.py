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
"""Shared definitions for tests."""
from mockito import unstub
import pytest

from iqm.iqm_client import QuantumArchitectureSpecification
from tests.move_architecture.move_architecture import move_architecture_specification, ndonis_architecture_specification


@pytest.fixture(autouse=True)
def reset_mocks_after_tests():
    yield
    unstub()


@pytest.fixture
def linear_architecture_3q():
    return QuantumArchitectureSpecification(
        name='3q_line',
        operations={'prx': [['QB1'], ['QB2'], ['QB3']], 'cz': [['QB1', 'QB2'], ['QB2', 'QB3']]},
        qubits=['QB1', 'QB2', 'QB3'],
        qubit_connectivity=[['QB1', 'QB2'], ['QB2', 'QB3']],
    )


@pytest.fixture
def adonis_architecture():
    return QuantumArchitectureSpecification(
        name='Adonis',
        operations={
            'prx': [['QB1'], ['QB2'], ['QB3'], ['QB4'], ['QB5']],
            'cz': [['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
            'measure': [['QB1'], ['QB2'], ['QB3'], ['QB4'], ['QB5']],
            'barrier': [],
        },
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5'],
        qubit_connectivity=[['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
    )


@pytest.fixture()
def new_architecture() -> QuantumArchitectureSpecification:
    return QuantumArchitectureSpecification(**move_architecture_specification)


@pytest.fixture
def adonis_architecture_shuffled_names():
    return QuantumArchitectureSpecification(
        name='Adonis',
        operations={
            'prx': [['QB2'], ['QB3'], ['QB1'], ['QB5'], ['QB4']],
            'cz': [['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
            'measure': [['QB2'], ['QB3'], ['QB1'], ['QB5'], ['QB4']],
            'barrier': [],
        },
        qubits=['QB2', 'QB3', 'QB1', 'QB5', 'QB4'],
        qubit_connectivity=[['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
    )


@pytest.fixture
def adonis_coupling_map():
    return {(0, 2), (2, 0), (1, 2), (2, 1), (2, 3), (3, 2), (2, 4), (4, 2)}


@pytest.fixture
def ndonis_architecture() -> QuantumArchitectureSpecification:
    return QuantumArchitectureSpecification(**ndonis_architecture_specification)


@pytest.fixture
def apollo_coupling_map():
    return {
        (0, 1),
        (1, 0),
        (0, 3),
        (3, 0),
        (1, 4),
        (4, 1),
        (2, 3),
        (3, 2),
        (7, 2),
        (2, 7),
        (3, 4),
        (4, 3),
        (8, 3),
        (3, 8),
        (4, 5),
        (5, 4),
        (9, 4),
        (4, 9),
        (5, 6),
        (6, 5),
        (10, 5),
        (5, 10),
        (11, 6),
        (6, 11),
        (7, 8),
        (8, 7),
        (7, 12),
        (12, 7),
        (8, 9),
        (9, 8),
        (8, 13),
        (13, 8),
        (9, 10),
        (10, 9),
        (9, 14),
        (14, 9),
        (10, 11),
        (11, 10),
        (15, 10),
        (10, 15),
        (16, 11),
        (11, 16),
        (12, 13),
        (13, 12),
        (13, 14),
        (14, 13),
        (17, 13),
        (13, 17),
        (15, 14),
        (14, 15),
        (18, 14),
        (14, 18),
        (15, 16),
        (16, 15),
        (15, 19),
        (19, 15),
        (17, 18),
        (18, 17),
        (18, 19),
        (19, 18),
    }
