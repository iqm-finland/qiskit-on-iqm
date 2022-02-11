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
from qiskit.providers import JobV1 as Job, JobStatus
from qiskit.result import Result
from qiskit.result.models import ExperimentResultData


class IQMJob(Job):
    def submit(self):
        raise NotImplementedError

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
