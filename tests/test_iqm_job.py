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

import mockito
import pytest
from iqm_client.iqm_client import (CircuitExecutionError, IQMClient, RunResult,
                                   RunStatus)
from mockito import mock, when
from qiskit.providers import JobStatus
from qiskit.result import Counts
from qiskit.result import Result as QiskitResult

from qiskit_iqm import IQMBackend, IQMJob


@pytest.fixture()
def job():
    client = mock(IQMClient)
    backend = IQMBackend(client)
    return IQMJob(backend, str(uuid.uuid4()), shots=4)


@pytest.fixture()
def iqm_result_single_register():
    return {
        'c_2_0_0': [[0], [1], [0], [1]],
        'c_2_0_1': [[1], [1], [1], [0]]
    }


@pytest.fixture()
def iqm_result_two_registers():
    return {
        'c_2_0_0': [[1], [0], [1], [0]],
        'c_2_0_1': [[1], [1], [0], [1]],
        'd_4_1_2': [[1], [1], [1], [1]]
    }


def test_submit_raises(job):
    with pytest.raises(NotImplementedError, match='Instead, use IQMBackend.run to submit jobs.'):
        job.submit()


def test_cancel_raises(job):
    with pytest.raises(NotImplementedError, match='Canceling jobs is currently not supported.'):
        job.cancel()


def test_status_for_ready_result(job):
    job._result = ['11', '10', '10']
    assert job.status() == JobStatus.DONE
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert result.get_memory() == ['11', '10', '10']


def test_status_done(job, iqm_result_single_register):
    client_result = RunResult(status=RunStatus.READY, measurements=iqm_result_single_register)
    when(job._client).get_run(uuid.UUID(job.job_id())).thenReturn(client_result)
    assert job.status() == JobStatus.DONE
    assert job._result is not None

    # Assert that repeated call does not query the client (i.e. works without calling the mocked get_run)
    assert job.status() == JobStatus.DONE
    mockito.verify(job._client, times=1).get_run(uuid.UUID(job.job_id()))


def test_status_running(job):
    when(job._client).get_run(uuid.UUID(job.job_id())).thenReturn(RunResult(status=RunStatus.PENDING))
    assert job.status() == JobStatus.RUNNING


def test_status_fail(job):
    when(job._client).get_run(uuid.UUID(job.job_id())).thenRaise(CircuitExecutionError)
    with pytest.raises(CircuitExecutionError):
        job.status()


def test_result(job, iqm_result_two_registers):
    client_result = RunResult(status=RunStatus.READY, measurements=iqm_result_two_registers)
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    result = job.result()

    assert isinstance(result, QiskitResult)
    assert result.get_memory() == ['0100 11', '0100 10', '0100 01', '0100 10']
    assert result.get_counts() == Counts({'0100 11': 1, '0100 10': 2, '0100 01': 1})

    # Assert that repeated call does not query the client (i.e. works without calling the mocked wait_for_results)
    # and call to status() does not call any functions from client.
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert job.status() == JobStatus.DONE
    mockito.verify(job._client, times=1).wait_for_results(uuid.UUID(job.job_id()))
