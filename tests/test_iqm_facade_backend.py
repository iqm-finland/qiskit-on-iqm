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
import re

from mockito import mock, when
import pytest
from qiskit import QuantumCircuit, transpile

from iqm.iqm_client import IQMClient
from iqm.qiskit_iqm.iqm_provider import IQMFacadeBackend


def test_run_fails_empty_cregs(adonis_architecture):
    circuit = QuantumCircuit(5, 5)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 2)
    circuit.measure_all()

    client = mock(IQMClient)
    when(client).get_dynamic_quantum_architecture(None).thenReturn(adonis_architecture)
    backend = IQMFacadeBackend(client)
    circuit_transpiled = transpile(circuit, backend=backend)

    with pytest.raises(ValueError, match='One or more circuits contain unused classical registers.'):
        backend.run(circuit_transpiled)


def test_backend_name(adonis_architecture):
    client = mock(IQMClient)
    when(client).get_dynamic_quantum_architecture(None).thenReturn(adonis_architecture)
    backend = IQMFacadeBackend(client)
    assert re.match(r'facade_adonis', backend.name)
