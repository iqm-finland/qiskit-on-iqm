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
import json
import warnings
from typing import Any, Dict

import qiskit_iqm_provider
from qiskit.providers import BackendV2 as Backend, Options
from qiskit.transpiler import Target

from qiskit_iqm_provider.qiskit_to_iqm import serialize_circuit, serialize_qubit_mapping


class IQMBackend(Backend):

    def __init__(self, url: str, settings_path: str, **fields):
        self._url = url
        self._settings_path = settings_path
        super().__init__(**fields)

    @property
    def url(self) -> str:
        return self._url

    @property
    def settings(self) -> Dict[str, Any]:
        with open(self._settings_path, 'r') as f:
            return json.loads(f.read())

    @property
    def target(self) -> Target:
        raise NotImplementedError

    @property
    def max_circuits(self):
        return 1

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1, qubit_mapping={})

    def run(self, circuit, shots=1, **kwargs):
        for option in kwargs:
            if not hasattr(self.options, option):
                warnings.warn(
                    "Option %s is not used by the IQM backend" % option,
                    UserWarning, stacklevel=2)

        circuit_json = serialize_circuit(circuit)
        mapping = serialize_qubit_mapping(kwargs['qubit_mapping'], circuit)

        job = qiskit_iqm_provider.IQMJob(backend=self, circuit_json=circuit_json, mapping_json=mapping, shots=shots)
        job.submit()
        return job

    def _submit(self, json):
        raise NotImplementedError
