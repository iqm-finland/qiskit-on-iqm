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

    def run(self, run_input, **options): ...


@pytest.fixture
def backend(linear_3q_architecture):
    return DummyIQMBackend(linear_3q_architecture)


def test_qubit_name_to_index_to_qubit_name(adonis_architecture):
    backend = DummyIQMBackend(adonis_architecture)

    for idx, name in backend._idx_to_qb.items():
        assert backend.index_to_qubit_name(idx) == name
        assert backend.qubit_name_to_index(name) == idx

    with pytest.raises(ValueError, match='Qubit index 7 is not found on the backend.'):
        backend.index_to_qubit_name(7)
    with pytest.raises(ValueError, match='Qubit \'Alice\' is not found on the backend.'):
        backend.qubit_name_to_index('Alice')


def test_transpile(backend):
    circuit = QuantumCircuit(3, 3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 0)

    circuit_transpiled = transpile(circuit, backend=backend)

    assert backend.target is not None
    cmap = backend.target.build_coupling_map()
    assert cmap is not None
    cmap = cmap.get_edges()
    for instr in circuit_transpiled.data:
        instruction = instr.operation
        qubits = instr.qubits
        assert instruction.name in ('r', 'cz')
        if instruction.name == 'cz':
            idx1 = circuit_transpiled.find_bit(qubits[0]).index
            idx2 = circuit_transpiled.find_bit(qubits[1]).index
            assert ((idx1, idx2) in cmap) or ((idx2, idx1) in cmap)
