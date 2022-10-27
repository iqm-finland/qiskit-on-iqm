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
from iqm_client import QuantumArchitectureSpecification
import pytest


@pytest.fixture
def linear_architecture_3q():
    return QuantumArchitectureSpecification(
        name='3q_line',
        operations=['cz'],
        qubits=['QB1', 'QB2', 'QB3'],
        qubit_connectivity=[['QB1', 'QB2'], ['QB2', 'QB3']],
    )


@pytest.fixture
def adonis_architecture():
    return QuantumArchitectureSpecification(
        name='Adonis',
        operations=['phased_rx', 'cz', 'measurement', 'barrier'],
        qubits=['QB1', 'QB2', 'QB3', 'QB4', 'QB5'],
        qubit_connectivity=[['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
    )


@pytest.fixture
def adonis_architecture_shuffled_names():
    return QuantumArchitectureSpecification(
        name='Adonis',
        operations=['phased_rx', 'cz', 'measurement', 'barrier'],
        qubits=['QB2', 'QB3', 'QB1', 'QB5', 'QB4'],
        qubit_connectivity=[['QB1', 'QB3'], ['QB2', 'QB3'], ['QB4', 'QB3'], ['QB5', 'QB3']],
    )
