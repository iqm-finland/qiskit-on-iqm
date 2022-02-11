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

from iqm_client.iqm_client import IQMClient
from qiskit.providers import BackendV2 as Backend, Options
from qiskit.transpiler import Target

from qiskit_iqm_provider.iqm_job import IQMJob
from qiskit_iqm_provider.qiskit_to_iqm import serialize_circuit, serialize_qubit_mapping


class IQMBackend(Backend):
    @property
    def target(self) -> Target:
        raise NotImplementedError

    @property
    def max_circuits(self):
        return 1

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1, qubit_mapping={})

    def run(self, circuit, **kwargs):
        for option in kwargs:
            if not hasattr(option, self.options):
                warnings.warn(
                    "Option %s is not used by the IQM backend" % option,
                    UserWarning, stacklevel=2)

        circuit_json = serialize_circuit(circuit)
        mapping_json = serialize_qubit_mapping(kwargs['qubit_mapping'], circuit)

        # FIXME: this job submitting logic should be somehow moved to IQMJob.
        client = IQMClient('url', {'some': 'settings'})
        job_id = client.submit_circuit(circuit_json, qubit_mapping=mapping_json, shots=kwargs['shots'])
        return IQMJob(backend=self, job_id=str(job_id))

    def _submit(self, json):
        raise NotImplementedError
