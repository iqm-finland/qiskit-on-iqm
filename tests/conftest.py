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
                        loci=(('QB1', 'QB3'), ('QB2', 'QB3'), ('QB3', 'QB4'), ('QB3', 'QB5'))
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
                        loci=(('QB1', 'QB3'), ('QB2', 'QB3'), ('QB3', 'QB4'), ('QB3', 'QB5'))
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
    return {(0, 2), (1, 2), (2, 3), (2, 4)}


@pytest.fixture
def deneb_coupling_map():
    return {(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)}


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
