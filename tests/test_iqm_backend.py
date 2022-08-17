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
import uuid

import numpy as np
import pytest
from iqm_client import IQMClient
from mockito import mock, when
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

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
    job = backend.retrieve_job('a job id')
    assert job.backend() == backend
    assert job.job_id() == 'a job id'


def test_max_circuits(backend):
    assert backend.max_circuits is None


def test_run_single_circuit(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    when(backend.client).submit_circuits([circuit_ser],
                                         qubit_mapping=None,
                                         settings=None,
                                         calibration_set_id=None,
                                         shots=shots
                                         ).thenReturn(some_id)
    job = backend.run(circuit, qubit_mapping=None, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit], qubit_mapping=None, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_run_with_non_default_settings(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    settings = {'setting1': 5}
    when(backend.client).submit_circuits([circuit_ser],
                                        qubit_mapping=None,
                                        settings=settings,
                                        calibration_set_id=None,
                                        shots=shots
                                        ).thenReturn(some_id)

    backend.run([circuit], qubit_mapping=None, settings=settings, shots=shots)


def test_run_with_custom_calibration_set_id(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    calibration_set_id = 24
    when(backend.client).submit_circuits([circuit_ser],
                                        qubit_mapping=None,
                                        settings=None,
                                        calibration_set_id=calibration_set_id,
                                        shots=shots
                                        ).thenReturn(some_id)

    backend.run([circuit], qubit_mapping=None, settings=None, calibration_set_id=calibration_set_id, shots=shots)


def test_run_circuit_with_qubit_mapping(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    circuit_ser = serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    when(backend.client).submit_circuits(
        [circuit_ser],
        qubit_mapping={'qubit_0': 'QB1'},
        settings=None,
        calibration_set_id=None,
        shots=shots
    ).thenReturn(some_id)

    job = backend.run(circuit, qubit_mapping={circuit.qubits[0]: 'QB1'}, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_run_batch_of_circuits(backend):
    qc = QuantumCircuit(2)
    theta = Parameter('theta')
    theta_range = np.linspace(0, 2*np.pi, 3)
    shots = 10
    some_id = uuid.uuid4()
    qc.cz(0,1)
    qc.r(theta, 0, 0)
    qc.cz(0,1)
    circuits = [qc.bind_parameters({theta: t}) for t in theta_range]
    circuits_serialized = [serialize_circuit(circuit) for circuit in circuits]
    when(backend.client).submit_circuits(
        circuits_serialized,
        qubit_mapping={'qubit_0': 'QB1', 'qubit_1': 'QB2'},
        settings=None,
        calibration_set_id=None,
        shots=shots
    ).thenReturn(some_id)

    job = backend.run(
        circuits,
        qubit_mapping={qc.qubits[0]: 'QB1', qc.qubits[1]: 'QB2'},
        shots=shots
    )
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_error_on_empty_circuit_list(backend):
    with pytest.raises(ValueError, match='Empty list of circuits submitted for execution.'):
        backend.run(
            [],
            qubit_mapping={},
            shots=42
        )


def test_close_client(backend):
    when(backend.client).close_auth_session().thenReturn(True)
    try:
        backend.close_client()
    except Exception as exc:  # pylint: disable=broad-except
        assert False, f'backend raised an exception {exc} on .close_client()'
