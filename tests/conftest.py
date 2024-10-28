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
        operations={'prx': [['QB1'], ['QB2'], ['QB3']], 'cz': [['QB1', 'QB2'], ['QB2', 'QB3']]},
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
def adonis_shuffled_names_architecture():
    """Like adonis_architecture, but relative order of loci has been shuffled."""
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('59478539-dcef-4b2e-80c8-122d7ec3fc89'),
        qubits=['QB2', 'QB3', 'QB1', 'QB5', 'QB4'],
        computational_resonators=[],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(loci=(('QB2',), ('QB3',), ('QB1',), ('QB5',), ('QB4',)))
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cc_prx': GateInfo(
                implementations={
                    'prx_composite': GateImplementationInfo(loci=(('QB5',), ('QB3',), ('QB2',), ('QB4',), ('QB1',)))
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
                    'constant': GateImplementationInfo(loci=(('QB2',), ('QB3',), ('QB1',), ('QB5',), ('QB4',)))
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
        computational_resonators=['COMP_R'],
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
                            ('QB1', 'COMP_R'),
                            ('QB2', 'COMP_R'),
                            ('QB3', 'COMP_R'),
                            ('QB4', 'COMP_R'),
                            ('QB5', 'COMP_R'),
                        )
                    ),
                },
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'move': GateInfo(
                implementations={
                    'tgss_crf': GateImplementationInfo(loci=(('QB6', 'COMP_R'),)),
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
    return {(0, 2), (2, 0), (1, 2), (2, 1), (2, 3), (3, 2), (2, 4), (4, 2)}


@pytest.fixture
def deneb_coupling_map():
    return {(1, 0), (0, 1), (2, 0), (0, 2), (3, 0), (0, 3), (4, 0), (0, 4), (5, 0), (0, 5), (6, 0), (0, 6)}


@pytest.fixture
def ndonis_architecture():
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6'],
        computational_resonators=['COMP_R'],
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
                            ('QB1', 'COMP_R'),
                            ('QB2', 'COMP_R'),
                            ('QB3', 'COMP_R'),
                            ('QB4', 'COMP_R'),
                            ('QB5', 'COMP_R'),
                            ('QB6', 'COMP_R'),
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
                            ('QB1', 'COMP_R'),
                            ('QB2', 'COMP_R'),
                            ('QB3', 'COMP_R'),
                            ('QB4', 'COMP_R'),
                            ('QB5', 'COMP_R'),
                            ('QB6', 'COMP_R'),
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


@pytest.fixture
def aphrodite_coupling_map():
    return {
        (0, 1),
        (1, 0),
        (0, 4),
        (4, 0),
        (1, 5),
        (5, 1),
        (2, 3),
        (3, 2),
        (2, 8),
        (8, 2),
        (3, 4),
        (4, 3),
        (3, 9),
        (9, 3),
        (4, 5),
        (5, 4),
        (4, 10),
        (10, 4),
        (5, 6),
        (6, 5),
        (5, 11),
        (11, 5),
        (6, 12),
        (12, 6),
        (7, 8),
        (8, 7),
        (7, 15),
        (15, 7),
        (8, 9),
        (9, 8),
        (8, 16),
        (16, 8),
        (9, 10),
        (10, 9),
        (9, 17),
        (17, 9),
        (10, 11),
        (11, 10),
        (10, 18),
        (18, 10),
        (11, 12),
        (12, 11),
        (11, 19),
        (19, 11),
        (12, 13),
        (13, 12),
        (12, 20),
        (20, 12),
        (13, 21),
        (21, 13),
        (14, 15),
        (15, 14),
        (14, 22),
        (22, 14),
        (15, 16),
        (16, 15),
        (15, 23),
        (23, 15),
        (16, 17),
        (17, 16),
        (16, 24),
        (24, 16),
        (17, 18),
        (18, 17),
        (17, 25),
        (25, 17),
        (18, 19),
        (19, 18),
        (18, 26),
        (26, 18),
        (19, 20),
        (20, 19),
        (19, 27),
        (27, 19),
        (20, 21),
        (21, 20),
        (20, 28),
        (28, 20),
        (21, 29),
        (29, 21),
        (22, 23),
        (23, 22),
        (23, 24),
        (24, 23),
        (23, 31),
        (31, 23),
        (24, 25),
        (25, 24),
        (24, 32),
        (32, 24),
        (25, 26),
        (26, 25),
        (25, 33),
        (33, 25),
        (26, 27),
        (27, 26),
        (26, 34),
        (34, 26),
        (27, 28),
        (28, 27),
        (27, 35),
        (35, 27),
        (28, 29),
        (29, 28),
        (28, 36),
        (36, 28),
        (29, 30),
        (30, 29),
        (29, 37),
        (37, 29),
        (30, 38),
        (38, 30),
        (31, 32),
        (32, 31),
        (31, 39),
        (39, 31),
        (32, 33),
        (33, 32),
        (32, 40),
        (40, 32),
        (33, 34),
        (34, 33),
        (33, 41),
        (41, 33),
        (34, 35),
        (35, 34),
        (34, 42),
        (42, 34),
        (35, 36),
        (36, 35),
        (35, 43),
        (43, 35),
        (36, 37),
        (37, 36),
        (36, 44),
        (44, 36),
        (37, 38),
        (38, 37),
        (37, 45),
        (45, 37),
        (39, 40),
        (40, 39),
        (40, 41),
        (41, 40),
        (40, 46),
        (46, 40),
        (41, 42),
        (42, 41),
        (41, 47),
        (47, 41),
        (42, 43),
        (43, 42),
        (42, 48),
        (48, 42),
        (43, 44),
        (44, 43),
        (43, 49),
        (49, 43),
        (44, 45),
        (45, 44),
        (44, 50),
        (50, 44),
        (46, 47),
        (47, 46),
        (47, 48),
        (48, 47),
        (47, 51),
        (51, 47),
        (48, 49),
        (49, 48),
        (48, 52),
        (52, 48),
        (49, 50),
        (50, 49),
        (49, 53),
        (53, 49),
        (51, 52),
        (52, 51),
        (52, 53),
        (53, 52),
    }
