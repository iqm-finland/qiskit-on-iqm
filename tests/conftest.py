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
from uuid import UUID

from mockito import unstub
import pytest

from iqm.iqm_client import (
    DynamicQuantumArchitecture,
    GateImplementationInfo,
    GateInfo,
    QuantumArchitectureSpecification,
)


@pytest.fixture(autouse=True)
def reset_mocks_after_tests():
    yield
    unstub()


@pytest.fixture
def linear_3q_architecture_static():
    return QuantumArchitectureSpecification(
        name='3q_line',
        operations={
            'prx': [['QB1'], ['QB2'], ['QB3']],
            'cz': [['QB1', 'QB2'], ['QB2', 'QB3']],
            'measure': [['QB1'], ['QB2'], ['QB3']],
        },
        qubits=['QB1', 'QB2', 'QB3'],
        qubit_connectivity=[['QB1', 'QB2'], ['QB2', 'QB3']],
    )


@pytest.fixture
def linear_3q_architecture():
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('59478539-dcef-4b2e-80c8-122d7ec3fc89'),
        qubits=['QB1', 'QB2', 'QB3'],
        computational_resonators=[],
        gates={
            'prx': GateInfo(
                implementations={'drag_gaussian': GateImplementationInfo(loci=(('QB1',), ('QB2',), ('QB3',)))},
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={'tgss': GateImplementationInfo(loci=(('QB1', 'QB2'), ('QB2', 'QB3')))},
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={'constant': GateImplementationInfo(loci=(('QB1',), ('QB2',), ('QB3',)))},
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def adonis_architecture():
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('59478539-dcef-4b2e-80c8-122d7ec3fc89'),
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5'],
        computational_resonators=[],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',)))
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cc_prx': GateInfo(
                implementations={
                    'prx_composite': GateImplementationInfo(loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',)))
                },
                default_implementation='prx_composite',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={
                    'tgss': GateImplementationInfo(
                        loci=(('QB1', 'QB3'), ('QB2', 'QB3'), ('QB4', 'QB3'), ('QB5', 'QB3'))
                    )
                },
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={
                    'constant': GateImplementationInfo(loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',)))
                },
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def move_architecture():
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6'],
        computational_resonators=['CR1'],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',))
                    ),
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={
                    'tgss': GateImplementationInfo(
                        loci=(
                            ('QB1', 'CR1'),
                            ('QB2', 'CR1'),
                            ('QB3', 'CR1'),
                            ('QB4', 'CR1'),
                            ('QB5', 'CR1'),
                        )
                    ),
                },
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'move': GateInfo(
                implementations={
                    'tgss_crf': GateImplementationInfo(loci=(('QB6', 'CR1'),)),
                },
                default_implementation='tgss_crf',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={
                    'constant': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',))
                    ),
                },
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture()
def hypothetical_fake_architecture():
    """Generate a hypothetical fake device for testing.

          QB1   QB2
           |    |
             CR1
           |*    *
    QB3 - QB4   QB7 - QB8
           |*    *
             CR2
            |   |
          QB5   QB6

    Here, '|' signifies a CZ connection and the '*' signify a move connection.

    """
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6', 'QB7', 'QB8'],
        computational_resonators=['CR1', 'CR2'],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',), ('QB7',), ('QB8',))
                    ),
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={
                    'tgss': GateImplementationInfo(
                        loci=(
                            ('QB1', 'CR1'),
                            ('QB2', 'CR1'),
                            ('QB3', 'QB4'),
                            ('QB4', 'CR1'),
                            ('QB4', 'CR2'),
                            ('QB5', 'CR2'),
                            ('QB6', 'CR2'),
                            ('QB7', 'QB8'),
                        )
                    ),
                },
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'move': GateInfo(
                implementations={
                    'tgss_crf': GateImplementationInfo(
                        loci=(
                            ('QB4', 'CR1'),
                            ('QB4', 'CR2'),
                            ('QB7', 'CR1'),
                            ('QB7', 'CR2'),
                        ),
                    )
                },
                default_implementation='tgss_crf',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={
                    'constant': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',), ('QB7',), ('QB8',)),
                    )
                },
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def ndonis_architecture():
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6'],
        computational_resonators=['CR1'],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',))
                    ),
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={
                    'tgss': GateImplementationInfo(
                        loci=(
                            ('QB1', 'CR1'),
                            ('QB2', 'CR1'),
                            ('QB3', 'CR1'),
                            ('QB4', 'CR1'),
                            ('QB5', 'CR1'),
                            ('QB6', 'CR1'),
                        )
                    ),
                },
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'move': GateInfo(
                implementations={
                    'tgss_crf': GateImplementationInfo(
                        loci=(
                            ('QB1', 'CR1'),
                            ('QB2', 'CR1'),
                            ('QB3', 'CR1'),
                            ('QB4', 'CR1'),
                            ('QB5', 'CR1'),
                            ('QB6', 'CR1'),
                        )
                    ),
                },
                default_implementation='tgss_crf',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={
                    'constant': GateImplementationInfo(
                        loci=(('QB1',), ('QB2',), ('QB3',), ('QB4',), ('QB5',), ('QB6',))
                    ),
                },
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def adonis_coupling_map():
    return {
        (0, 2),
        (1, 2),
        (3, 2),
        (4, 2),
    }


@pytest.fixture
def apollo_coupling_map():
    return {
        (0, 1),
        (0, 3),
        (1, 4),
        (2, 3),
        (7, 2),
        (3, 4),
        (8, 3),
        (4, 5),
        (9, 4),
        (5, 6),
        (10, 5),
        (11, 6),
        (7, 8),
        (7, 12),
        (8, 9),
        (8, 13),
        (9, 10),
        (9, 14),
        (10, 11),
        (15, 10),
        (16, 11),
        (12, 13),
        (13, 14),
        (17, 13),
        (15, 14),
        (18, 14),
        (15, 16),
        (15, 19),
        (17, 18),
        (18, 19),
    }


@pytest.fixture
def aphrodite_coupling_map():
    return {
        (0, 1),
        (0, 4),
        (1, 5),
        (2, 3),
        (2, 8),
        (3, 4),
        (3, 9),
        (4, 5),
        (4, 10),
        (5, 6),
        (5, 11),
        (6, 12),
        (7, 8),
        (7, 15),
        (8, 9),
        (8, 16),
        (9, 10),
        (9, 17),
        (10, 11),
        (10, 18),
        (11, 12),
        (11, 19),
        (12, 13),
        (12, 20),
        (13, 21),
        (14, 15),
        (14, 22),
        (15, 16),
        (15, 23),
        (16, 17),
        (16, 24),
        (17, 18),
        (17, 25),
        (18, 19),
        (18, 26),
        (19, 20),
        (19, 27),
        (20, 21),
        (20, 28),
        (21, 29),
        (22, 23),
        (23, 24),
        (23, 31),
        (24, 25),
        (24, 32),
        (25, 26),
        (25, 33),
        (26, 27),
        (26, 34),
        (27, 28),
        (27, 35),
        (28, 29),
        (28, 36),
        (29, 30),
        (29, 37),
        (30, 38),
        (31, 32),
        (31, 39),
        (32, 33),
        (32, 40),
        (33, 34),
        (33, 41),
        (34, 35),
        (34, 42),
        (35, 36),
        (35, 43),
        (36, 37),
        (36, 44),
        (37, 38),
        (37, 45),
        (39, 40),
        (40, 41),
        (40, 46),
        (41, 42),
        (41, 47),
        (42, 43),
        (42, 48),
        (43, 44),
        (43, 49),
        (44, 45),
        (44, 50),
        (46, 47),
        (47, 48),
        (47, 51),
        (48, 49),
        (48, 52),
        (49, 50),
        (49, 53),
        (51, 52),
        (52, 53),
    }
