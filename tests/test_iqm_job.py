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
import uuid

from iqm_client.iqm_client import CircuitExecutionError, IQMClient, RunResult, RunStatus
from mockito import mock, when
import pytest
from qiskit.result import Result as QiskitResult, Counts
from qiskit.providers import JobStatus

from qiskit_iqm import IQMBackend, IQMJob


@pytest.fixture()
def job():
    client = mock(IQMClient)
    backend = IQMBackend(client)
    return IQMJob(backend, str(uuid.uuid4()))


def test_submit_raises(job):
    with pytest.raises(NotImplementedError, match='Instead, use run method of backend to submit jobs.'):
        job.submit()


def test_cancel_raises(job):
    with pytest.raises(NotImplementedError, match='Canceling jobs is currently not supported.'):
        job.cancel()


def test_status_for_ready_result(job):
    job._result = ['11', '10', '10']
    assert job.status() == JobStatus.DONE


def test_status_done(job):
    client_result = RunResult(status=RunStatus.READY, measurements={'mk': [(1, 1), (1, 0), (1, 0)]})
    when(job._client).get_run(uuid.UUID(job.job_id())).thenReturn(client_result)
    assert job.status() == JobStatus.DONE
    assert job._result is not None

    # Assert that repeated call does not query the client (i.e. works without mocking get_run)
    assert job.status() == JobStatus.DONE


def test_status_running(job):
    when(job._client).get_run(uuid.UUID(job.job_id())).thenReturn(RunResult(status=RunStatus.PENDING))
    assert job.status() == JobStatus.RUNNING


def test_status_fail(job):
    when(job._client).get_run(uuid.UUID(job.job_id())).thenRaise(CircuitExecutionError)
    assert job.status() == JobStatus.ERROR


def test_result(job):
    client_result = RunResult(status=RunStatus.READY, measurements={'mk': [(1, 1), (1, 0), (1, 0)]})
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    result = job.result()
    assert job.status() == JobStatus.DONE

    assert isinstance(result, QiskitResult)
    assert result.get_memory() == ['11', '10', '10']
    assert result.get_counts() == Counts({'11': 1, '10': 2})
