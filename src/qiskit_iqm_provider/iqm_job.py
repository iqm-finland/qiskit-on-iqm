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
from typing import List

from iqm_client.iqm_client import IQMClient, Circuit, SingleQubitMapping
from qiskit.providers import JobV1 as Job, JobStatus
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
        client = IQMClient(self.backend().url, self.backend().settings)
        job_id = client.submit_circuit(self.circuit_json, qubit_mapping=self.mapping_json, shots=self.shots)
        self._job_id = str(job_id)

    def result(self):
        # Rough sketch of implementation
        # 1. get result from iqm client
        # 2. extract measurement results: a=result.measurements['mk']
        # 3. Construct Qiskit ExperimentResultData object with b=ExperimentResultData(memory=a)
        # 4. return Result([b])
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError

    def status(self) -> JobStatus:
        raise NotImplementedError
