# Copyright 2022-2023 Qiskit on IQM developers
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

"""Testing IQM backend.
"""
from typing import Optional

import pytest
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.providers import Options

from iqm.qiskit_iqm.iqm_backend import IQMBackendBase


class DummyIQMBackend(IQMBackendBase):
    """Dummy implementation for abstract methods of IQMBacked, so that instances can be created
    and the rest of functionality tested."""

    @classmethod
    def _default_options(cls) -> Options:
        return Options()

    @property
    def max_circuits(self) -> Optional[int]:
        return None

    def run(self, run_input, **options):
        ...


@pytest.fixture
def backend(linear_architecture_3q):
    return DummyIQMBackend(linear_architecture_3q)


def test_qubit_name_to_index_to_qubit_name(adonis_architecture_shuffled_names):
    backend = DummyIQMBackend(adonis_architecture_shuffled_names)

    correct_idx_name_associations = set(enumerate(['QB1', 'QB2', 'QB3', 'QB4', 'QB5']))
    assert all(backend.index_to_qubit_name(idx) == name for idx, name in correct_idx_name_associations)
    assert all(backend.qubit_name_to_index(name) == idx for idx, name in correct_idx_name_associations)

    assert backend.index_to_qubit_name(7) is None
    assert backend.qubit_name_to_index('Alice') is None


def test_transpile(backend):
    circuit = QuantumCircuit(3, 3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 0)

    circuit_transpiled = transpile(circuit, backend=backend)
    cmap = backend.coupling_map.get_edges()
    for instruction, qubits, _ in circuit_transpiled.data:
        assert instruction.name in ('r', 'cz')
        if instruction.name == 'cz':
            idx1 = circuit_transpiled.find_bit(qubits[0]).index
            idx2 = circuit_transpiled.find_bit(qubits[1]).index
            assert ((idx1, idx2) in cmap) or ((idx2, idx1) in cmap)


def test_validate_compatible_architecture(
    adonis_architecture, adonis_architecture_shuffled_names, linear_architecture_3q
):
    backend = DummyIQMBackend(adonis_architecture)
    assert backend.validate_compatible_architecture(adonis_architecture) is True
    assert backend.validate_compatible_architecture(adonis_architecture_shuffled_names) is True
    assert backend.validate_compatible_architecture(linear_architecture_3q) is False
