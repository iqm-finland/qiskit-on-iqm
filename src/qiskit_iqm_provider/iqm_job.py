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
from datetime import date
from typing import List

from iqm_client.iqm_client import IQMClient, Circuit, SingleQubitMapping
from qiskit.providers import JobV1 as Job, JobStatus
from qiskit.result import Result
from qiskit_iqm_provider import IQMBackend


class IQMJob(Job):

    def __init__(self,
                 backend: IQMBackend,
                 circuit_json:
                 Circuit, mapping_json: List[SingleQubitMapping],
                 shots: int,
                 **kwargs):
        self.circuit_json = circuit_json
        self.mapping_json = mapping_json
        self.shots = shots
        self._status = None
        self._client = IQMClient(backend.url, backend.settings)
        self._job_id = None
        if 'job_id' in kwargs:
            job_id = kwargs['job_id']
            del kwargs['job_id']
        else:
            job_id = 'pending'  # Users should not create jobs without job_id
        super().__init__(backend, job_id=job_id, **kwargs)

    def backend(self) -> IQMBackend:
        """Return the backend where this job was executed."""
        if not isinstance(self._backend, IQMBackend):
            raise TypeError("Backend of IQMJob should be an IQMBackend")
        return self._backend

    def submit(self):
        job_id = self._client.submit_circuit(self.circuit_json, qubit_mapping=self.mapping_json, shots=self.shots)
        self._job_id = job_id.hex
        self._status = JobStatus.RUNNING

    def result(self) -> Result:
        if self.status() != JobStatus.RUNNING and self.status() != JobStatus.DONE:
            raise RuntimeError  # TODO custom Exception
        result = self._client.wait_for_results(uuid.UUID(self._job_id))
        self._status = JobStatus.DONE
        # Qiskit needs bitstrings in hex. FIXME: how to achieve this in a less ugly way? :D
        measurements = [hex(int(''.join(str(bit) for bit in row), 2)) for row in result.measurements['mk']]
        result_dict = {
            'backend_name': None,
            'backend_version': None,
            'qobj_id': None,
            'job_id': self._job_id,
            'success': True,
            'results': [{'memory': measurements}],
            'date': date.today()
        }
        # Use factory method to create results instead of manually constructing it, so that all methods work properly,
        # for example you can now call the get_counts() method on the results object and get proper data.
        return Result.from_dict(result_dict)

    def cancel(self):
        pass

    def status(self) -> JobStatus:
        return self._status

