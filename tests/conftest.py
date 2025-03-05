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


def _1q_loci(qubits: list[str]) -> tuple[tuple[str, ...], ...]:
    """One-qubit loci for the given qubits."""
    return tuple((q,) for q in qubits)


@pytest.fixture
def linear_3q_architecture():
    qubits = ['QB1', 'QB2', 'QB3']
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('59478539-dcef-4b2e-80c8-122d7ec3fc89'),
        qubits=qubits,
        computational_resonators=[],
        gates={
            'prx': GateInfo(
                implementations={'drag_gaussian': GateImplementationInfo(loci=_1q_loci(qubits))},
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cz': GateInfo(
                implementations={'tgss': GateImplementationInfo(loci=(('QB1', 'QB2'), ('QB2', 'QB3')))},
                default_implementation='tgss',
                override_default_implementation={},
            ),
            'measure': GateInfo(
                implementations={'constant': GateImplementationInfo(loci=_1q_loci(qubits))},
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def adonis_architecture():
    qubits = ['QB1', 'QB2', 'QB3', 'QB4', 'QB5']
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('59478539-dcef-4b2e-80c8-122d7ec3fc89'),
        qubits=qubits,
        computational_resonators=[],
        gates={
            'prx': GateInfo(
                implementations={'drag_gaussian': GateImplementationInfo(loci=_1q_loci(qubits))},
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cc_prx': GateInfo(
                implementations={'prx_composite': GateImplementationInfo(loci=_1q_loci(qubits))},
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
                implementations={'constant': GateImplementationInfo(loci=_1q_loci(qubits))},
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )


@pytest.fixture
def move_architecture():
    qubits = ['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6']
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=qubits,
        computational_resonators=['CR1'],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(loci=_1q_loci(qubits)),
                },
                default_implementation='drag_gaussian',
                override_default_implementation={},
            ),
            'cc_prx': GateInfo(
                implementations={'prx_composite': GateImplementationInfo(loci=_1q_loci(qubits))},
                default_implementation='prx_composite',
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
                    'constant': GateImplementationInfo(loci=_1q_loci(qubits)),
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
    qubits = ['QB1', 'QB2', 'QB3', 'QB4', 'QB5', 'QB6']
    return DynamicQuantumArchitecture(
        calibration_set_id=UUID('26c5e70f-bea0-43af-bd37-6212ec7d04cb'),
        qubits=qubits,
        computational_resonators=['CR1'],
        gates={
            'prx': GateInfo(
                implementations={
                    'drag_gaussian': GateImplementationInfo(loci=_1q_loci(qubits)),
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
                    'constant': GateImplementationInfo(loci=_1q_loci(qubits)),
                },
                default_implementation='constant',
                override_default_implementation={},
            ),
        },
    )
