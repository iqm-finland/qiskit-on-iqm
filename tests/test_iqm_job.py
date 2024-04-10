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
import io
import uuid

import mockito
from mockito import mock, unstub, verify, when
import pytest
from qiskit import QuantumCircuit
from qiskit.providers import JobStatus
from qiskit.result import Counts
from qiskit.result import Result as QiskitResult
from qiskit.tools.monitor import job_monitor

from iqm.iqm_client import (
    HeraldingMode,
    Instruction,
    IQMClient,
    JobAbortionError,
    RunResult,
    RunStatus,
    SingleQubitMapping,
    Status,
)
from iqm.qiskit_iqm.iqm_job import IQMJob
from iqm.qiskit_iqm.iqm_provider import IQMBackend


@pytest.fixture()
def job(adonis_architecture):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(adonis_architecture)
    backend = IQMBackend(client)
    return IQMJob(backend, str(uuid.uuid4()))


@pytest.fixture()
def iqm_result_no_shots():
    return {'c_2_0_0': [], 'c_2_0_1': []}


@pytest.fixture()
def iqm_result_two_registers():
    return {'c_2_0_0': [[1], [0], [1], [0]], 'c_2_0_1': [[1], [1], [0], [1]], 'd_4_1_2': [[1], [1], [1], [1]]}


@pytest.fixture()
def iqm_metadata():
    measurement = Instruction(name='measure', implementation=None, qubits=('0',), args={'key': 'm1'})
    return {
        'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
        'request': {
            'shots': 4,
            'circuits': [{'name': 'circuit_1', 'instructions': (measurement,), 'metadata': {'a': 'b'}}],
            'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
            'qubit_mapping': [
                SingleQubitMapping(logical_name='0', physical_name='QB1'),
                SingleQubitMapping(logical_name='1', physical_name='QB2'),
            ],
        },
    }


@pytest.fixture()
def iqm_metadata_with_timestamps():
    measurement = Instruction(name='measure', implementation=None, qubits=('0',), args={'key': 'm1'})
    return {
        'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
        'request': {
            'shots': 4,
            'circuits': [{'name': 'circuit_1', 'instructions': (measurement,), 'metadata': {'a': 'b'}}],
            'calibration_set_id': 'df124054-f6d8-41f9-b880-8487f90018f9',
            'qubit_mapping': [
                SingleQubitMapping(logical_name='0', physical_name='QB1'),
                SingleQubitMapping(logical_name='1', physical_name='QB2'),
            ],
        },
        'timestamps': {
            'job_start': '2023-01-02T12:34:56.123456+00:00',
            'job_end': '2023-01-02T12:34:56.123456+03:00',
        },
    }


def test_submit_raises(job):
    with pytest.raises(NotImplementedError, match='You should never have to submit jobs by calling this method.'):
        job.submit()


def test_cancel_successful(job, recwarn):
    when(job._client).abort_job(uuid.UUID(job.job_id())).thenReturn(None)
    assert job.cancel() is True
    assert len(recwarn) == 0
    verify(job._client, times=1).abort_job(uuid.UUID(job.job_id()))
    unstub()


def test_cancel_failed(job):
    when(job._client).abort_job(uuid.UUID(job.job_id())).thenRaise(JobAbortionError)
    with pytest.warns(UserWarning, match='Failed to cancel job'):
        assert job.cancel() is False
    verify(job._client, times=1).abort_job(uuid.UUID(job.job_id()))
    unstub()


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


@pytest.mark.parametrize(
    'run_status,job_status',
    [
        (Status.PENDING_COMPILATION, JobStatus.QUEUED),
        (Status.PENDING_EXECUTION, JobStatus.RUNNING),
        (Status.FAILED, JobStatus.ERROR),
        (Status.ABORTED, JobStatus.CANCELLED),
    ],
)
def test_other_job_statuses(job, run_status: Status, job_status: JobStatus):
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(RunStatus(status=run_status))
    assert job.status() == job_status


def test_error_message(job, iqm_metadata):
    err_msg = 'The job failed with this error message'
    client_result = RunResult(status=Status.FAILED, message=err_msg, metadata=iqm_metadata)
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(client_result)
    assert job.status() == JobStatus.ERROR
    assert job.error_message() == err_msg


def test_error_message_on_successful_job(job, iqm_metadata):
    client_result = RunResult(status=Status.READY, metadata=iqm_metadata)
    when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(client_result)
    assert job.status() == JobStatus.DONE
    assert job.error_message() is None


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
    assert result.request.qubit_mapping == iqm_metadata['request']['qubit_mapping']

    # Assert that repeated call does not query the client (i.e. works without calling the mocked wait_for_results)
    # and call to status() does not call any functions from client.
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert job.status() == JobStatus.DONE
    mockito.verify(job._client, times=1).wait_for_results(uuid.UUID(job.job_id()))


def test_result_no_shots(job, iqm_result_no_shots, iqm_metadata):
    iqm_metadata['request']['heralding_mode'] = HeraldingMode.ZEROS
    client_result = RunResult(
        status=Status.READY,
        measurements=[iqm_result_no_shots],
        metadata=iqm_metadata,
    )
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    with pytest.warns(UserWarning, match='Received measurement results containing zero shots.'):
        result = job.result()

    assert isinstance(result, QiskitResult)
    assert result.get_memory() == []
    assert result.get_counts() == Counts({})


def test_result_multiple_circuits(job, iqm_result_two_registers):
    instruction_meta = [{'name': 'measure', 'qubits': ['0'], 'args': {'key': 'm1'}}]
    iqm_metadata_multiple_circuits = {
        'calibration_set_id': '9d75904b-0c93-461f-b1dc-bd200cfad1f1',
        'request': {
            'shots': 4,
            'circuits': [
                {'name': 'circuit_1', 'instructions': instruction_meta, 'metadata': {'a': 0}},
                {'name': 'circuit_2', 'instructions': instruction_meta, 'metadata': {'a': 1}},
            ],
            'calibration_set_id': '9d75904b-0c93-461f-b1dc-bd200cfad1f1',
            'qubit_mapping': [
                SingleQubitMapping(logical_name='0', physical_name='QB1'),
                SingleQubitMapping(logical_name='1', physical_name='QB2'),
                SingleQubitMapping(logical_name='2', physical_name='QB3'),
            ],
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
    assert result.request.qubit_mapping == iqm_metadata_multiple_circuits['request']['qubit_mapping']


def test_result_with_timestamps(job, iqm_result_two_registers, iqm_metadata_with_timestamps):
    client_result = RunResult(
        status=Status.READY,
        measurements=[iqm_result_two_registers],
        metadata=iqm_metadata_with_timestamps,
    )
    when(job._client).wait_for_results(uuid.UUID(job.job_id())).thenReturn(client_result)

    assert job.metadata.get('timestamps') is None
    result = job.result()
    assert 'timestamps' in job.metadata
    assert job.metadata.pop('timestamps') == iqm_metadata_with_timestamps.get('timestamps')
    assert 'timestamps' in result._metadata
    assert result.timestamps == iqm_metadata_with_timestamps.get('timestamps')


def test_job_monitor(job, iqm_metadata):
    client_result = RunResult(status=Status.READY, metadata=iqm_metadata)
    run_responses = [
        [RunStatus(status=Status.PENDING_COMPILATION), RunStatus(status=Status.ABORTED)],
        [RunStatus(status=Status.PENDING_COMPILATION)] * 2 + [RunStatus(status=Status.FAILED)],
        [RunStatus(status=Status.PENDING_COMPILATION)] * 2
        + [RunStatus(status=Status.PENDING_EXECUTION), client_result],
        [RunStatus(status=s.value) for s in Status],
    ]
    sep = '---'
    for responses in run_responses:
        when(job._client).get_run_status(uuid.UUID(job.job_id())).thenReturn(*responses)
        monitor_string = io.StringIO()
        job_monitor(job, output=monitor_string, line_discipline=sep, interval=0)
        monitor_string.close()
