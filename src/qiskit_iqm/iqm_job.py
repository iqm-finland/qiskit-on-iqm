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

"""
IQM Job
"""
from collections import Counter
from datetime import date
import uuid

from iqm_client.iqm_client import CircuitExecutionError, RunStatus
from qiskit.providers import JobV1 as Job, JobStatus
from qiskit.result import Result
from qiskit.result import Counts
from requests.exceptions import HTTPError

import qiskit_iqm


class IQMJob(Job):
    """IQM job

    Args:
        backend:
        circuit_json:
        **kwargs:
    """
    def __init__(self, backend: qiskit_iqm.IQMBackend, job_id: str, **kwargs):
        super().__init__(backend, job_id=job_id, **kwargs)
        self._result = None
        self._client = backend.client

    @staticmethod
    def _format_iqm_result(iqm_result):
        return [''.join(str(bit) for bit in row) for row in iqm_result.measurements['mk']]

    def submit(self):
        raise NotImplementedError('Instead, use run method of backend to submit jobs')

    def result(self) -> Result:
        result = self._client.wait_for_results(uuid.UUID(self._job_id))
        self._result = self._format_iqm_result(result)
        result_dict = {
            'backend_name': None,
            'backend_version': None,
            'qobj_id': None,
            'job_id': self._job_id,
            'success': True,
            'results': [
                {
                    'shots': len(self._result),
                    'success': True,
                    'data': {'memory': self._result, 'counts': Counts(Counter(self._result))}
                }
            ],
            'date': date.today()
        }
        return Result.from_dict(result_dict)

    def cancel(self):
        raise NotImplementedError('Canceling jobs is currently not supported.')

    def status(self) -> JobStatus:
        if self._result:
            return JobStatus.DONE

        try:
            result = self._client.get_run(self._job_id)
            if result.status == RunStatus.PENDING:
                return JobStatus.RUNNING
            if result.status == RunStatus.READY:
                self._result = self._format_iqm_result(result)
                return JobStatus.DONE
        except CircuitExecutionError:
            return JobStatus.ERROR
        except HTTPError:
            # FIXME: this scenario should be handled by IQMClient instead
            raise RuntimeError(f'Job with id {self._job_id} does not exist.')
