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
import warnings
from typing import Iterable, Union, List

from qiskit.providers import BackendV2 as Backend, QubitProperties
from qiskit_iqm_provider.iqm_job import IQMJob



class IQMBackend(Backend):
    @property
    def target(self):
        raise NotImplementedError

    @property
    def max_circuits(self):
        raise NotImplementedError

    @classmethod
    def _default_options(cls):
        raise NotImplementedError

    @property
    def dtm(self) -> float:
        raise NotImplementedError

    @property
    def meas_map(self) -> List[List[int]]:
        raise NotImplementedError

    def qubit_properties(self, qubit: Union[int, List[int]]) -> Union[QubitProperties, List[QubitProperties]]:
        raise NotImplementedError

    def drive_channel(self, qubit: int):
        raise NotImplementedError

    def measure_channel(self, qubit: int):
        raise NotImplementedError

    def acquire_channel(self, qubit: int):
        raise NotImplementedError

    def control_channel(self, qubits: Iterable[int]):
        raise NotImplementedError

    def run(self, circuit, **options):
        for option in options:
            if not hasattr(option, self.options):
                warnings.warn(
                    "Option %s is not used by the IQM backend" % option,
                    UserWarning, stacklevel=2)
        options = {
            'shots': options.get('shots', self.options.shots),
            'memory': options.get('memory', self.options.shots),
        }
        job_json = self._convert_to_iqm_json(circuit, options)
        job_handle = self._submit(job_json)
        return IQMJob(backend=self, job_id=job_handle)

    def _convert_to_iqm_json(self, circuit, options):
        raise NotImplementedError

    def _submit(self, iqm_json):
        raise NotImplementedError
