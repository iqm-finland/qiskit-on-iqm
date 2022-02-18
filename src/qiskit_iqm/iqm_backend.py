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
Implementation of Qiskit backend for IQM quantum computers.
"""
from iqm_client.iqm_client import IQMClient
from qiskit import QuantumCircuit
from qiskit.providers import BackendV2 as Backend, Options
from qiskit.transpiler import Target

import qiskit_iqm
from qiskit_iqm.qiskit_to_iqm import serialize_circuit, serialize_qubit_mapping


class IQMBackend(Backend):
    """Qiskit backend enabling execution of quantum circuits on IQM quantum computers.

    Args:
        client: IQMClient instance used for submitting circuits for execution on IQM server.
        **kwargs: Optional arguments to be passed to the parent Qiskit Backend initializer.
    """
    def __init__(self, client: IQMClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    @property
    def max_circuits(self) -> int:
        return 1

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1024, qubit_mapping=None)

    @property
    def target(self) -> Target:
        raise NotImplementedError

    def run(self, run_input: QuantumCircuit, **options) -> 'qiskit_iqm.IQMJob':
        qubit_mapping = options.get('qubit_mapping', self.options.qubit_mapping)
        shots = options.get('shots', self.options.shots)

        circuit_serialized = serialize_circuit(run_input)
        mapping_serialized = serialize_qubit_mapping(qubit_mapping, run_input)

        uuid = self.client.submit_circuit(circuit_serialized, mapping_serialized, shots=shots)
        return qiskit_iqm.IQMJob(self, str(uuid))

    def retrieve_job(self, job_id: str) -> 'qiskit_iqm.IQMJob':
        """Create and return an IQMJob instance associated with this backend with given job id.
        """
        return qiskit_iqm.IQMJob(self, job_id)
