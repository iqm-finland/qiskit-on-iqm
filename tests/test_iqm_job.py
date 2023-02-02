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

"""Testing IQMJob.
"""
import uuid

from iqm_client import IQMClient, RunResult, RunStatus, Status
import mockito
from mockito import mock, when
import pytest
from qiskit import QuantumCircuit
from qiskit.providers import JobStatus
from qiskit.result import Counts
from qiskit.result import Result as QiskitResult

from qiskit_iqm import IQMBackend, IQMJob


@pytest.fixture()
def job(adonis_architecture):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(adonis_architecture)
    backend = IQMBackend(client)
    return IQMJob(backend, str(uuid.uuid4()))


@pytest.fixture()
def iqm_result_single_register():
    return {'c_2_0_0': [[0], [1], [0], [1]], 'c_2_0_1': [[1], [1], [1], [0]]}


@pytest.fixture()
def iqm_result_two_registers():
    return {'c_2_0_0': [[1], [0], [1], [0]], 'c_2_0_1': [[1], [1], [0], [1]], 'd_4_1_2': [[1], [1], [1], [1]]}


@pytest.fixture()
def iqm_metadata():
    return {
        'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
        'request': {
            'shots': 4,
            'circuits': [{'name': 'circuit_1', 'instructions': [], 'metadata': {'a': 'b'}}],
            'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
        },
    }


def test_submit_raises(job):
    with pytest.raises(NotImplementedError, match='You should never have to submit jobs by calling this method.'):
        job.submit()


def test_cancel_raises(job):
    with pytest.raises(NotImplementedError, match='Canceling jobs is currently not supported.'):
        job.cancel()


def test_status_for_ready_result(job):
    job._result = [('circuit_1', ['11', '10', '10'])]
    assert job.status() == JobStatus.DONE
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert result.get_memory() == ['11', '10', '10']


def test_status_done(job, iqm_metadata):
    client_result = RunResult(status=Status.READY, measurements=None, metadata=iqm_metadata)
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(client_result)
    assert job.status() == JobStatus.DONE
    assert job._result is None


def test_status_running(job):
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(RunStatus(status=Status.PENDING))
    assert job.status() == JobStatus.RUNNING


def test_status_fail(job):
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(RunStatus(status=Status.FAILED))
    assert job.status() == JobStatus.ERROR


def test_result(job, iqm_result_two_registers, iqm_metadata):
    client_result = RunResult(
        status=Status.READY,
        measurements=[iqm_result_two_registers],
        metadata=iqm_metadata,
    )
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    result = job.result()

    assert isinstance(result, QiskitResult)
    assert result.get_memory() == ['0100 11', '0100 10', '0100 01', '0100 10']
    assert result.get_counts() == Counts({'0100 11': 1, '0100 10': 2, '0100 01': 1})
    for r in result.results:
        assert r.calibration_set_id == uuid.UUID('df124054-f6d8-41f9-b880-8487f90018f9')
        assert r.data.metadata == {'a': 'b'}

    # Assert that repeated call does not query the client (i.e. works without calling the mocked wait_for_results)
    # and call to status() does not call any functions from client.
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert job.status() == JobStatus.DONE
    mockito.verify(job._client, times=1).wait_for_results(uuid.UUID(job.job_id()))


def test_result_multiple_circuits(job, iqm_result_two_registers):
    iqm_metadata_multiple_circuits = {
        'calibration_set_id': '9d75904b-0c93-461f-b1dc-bd200cfad1f1',
        'request': {
            'shots': 4,
            'circuits': [
                {'name': 'circuit_1', 'instructions': [], 'metadata': {'a': 0}},
                {'name': 'circuit_2', 'instructions': [], 'metadata': {'a': 1}},
            ],
            'calibration_set_id': '9d75904b-0c93-461f-b1dc-bd200cfad1f1',
        },
    }
    client_result = RunResult(
        status=Status.READY,
        measurements=[iqm_result_two_registers, iqm_result_two_registers],
        metadata=iqm_metadata_multiple_circuits,
    )
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    result = job.result()

    assert isinstance(result, QiskitResult)
    for circuit_idx in range(2):
        assert result.get_memory(circuit_idx) == ['0100 11', '0100 10', '0100 01', '0100 10']
        assert result.get_counts(circuit_idx) == Counts({'0100 11': 1, '0100 10': 2, '0100 01': 1})
    assert result.get_counts(QuantumCircuit(name='circuit_1')) == Counts({'0100 11': 1, '0100 10': 2, '0100 01': 1})
    assert result.get_counts(QuantumCircuit(name='circuit_2')) == Counts({'0100 11': 1, '0100 10': 2, '0100 01': 1})
    for i, r in enumerate(result.results):
        assert r.calibration_set_id == uuid.UUID('9d75904b-0c93-461f-b1dc-bd200cfad1f1')
        assert r.data.metadata == {'a': i}
