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

"""Testing IQM backend.
"""
import os
import uuid

import pytest
from iqm_client import IQMClient
from mockito import mock, when
from qiskit import QuantumCircuit

from qiskit_iqm import IQMBackend, IQMJob
from qiskit_iqm.qiskit_to_iqm import serialize_circuit


@pytest.fixture
def backend():
    client = mock(IQMClient)
    return IQMBackend(client)


def test_default_options(backend):
    assert backend.options.shots == 1024
    assert backend.options.qubit_mapping is None


def test_retrieve_job(backend):
    job = backend.retrieve_job("a job id")
    assert job.backend() == backend
    assert job.job_id() == "a job id"


def test_max_circuits(backend):
    assert backend.max_circuits == 1


def test_run(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    when(backend.client).submit_circuit(circuit_ser, [], settings=None, shots=shots).thenReturn(some_id)

    job = backend.run(circuit, qubit_mapping={}, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit], qubit_mapping={}, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)

    # Should raise exception if more than one circuit is present in the list
    with pytest.raises(ValueError):
        backend.run([circuit, circuit])


def test_run_with_non_default_settings(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    settings_path = os.path.join(os.path.dirname(__file__), "resources", "test_settings.json")
    expected_settings = {"setting1": 5}
    when(backend.client).submit_circuit(circuit_ser, [], settings=expected_settings, shots=shots).thenReturn(some_id)

    backend.run(circuit, qubit_mapping={}, shots=shots, settings_path=settings_path)
