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
from qiskit.circuit import Qubit
from qiskit.providers import BackendV2 as Backend, Options
from qiskit.transpiler import Target

import qiskit_iqm
from qiskit_iqm.qiskit_to_iqm import serialize_circuit, serialize_qubit_mapping


class IQMBackend(Backend):
    """Qiskit backend enabling execution of quantum circuits on IQM quantum computers.

    Args:
        url: Endpoint for accessing the server interface. Has to start with http or https.
        settings_path: Path to a file containing settings for the quantum computer.
        **kwargs: Optional arguments to be passed to the parent Qiskit Backend initializer.
    """
    def __init__(self, client: IQMClient, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @property
    def client(self):
        return self._client

    @property
    def max_circuits(self) -> int:
        return 1

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1024, qubit_mapping={})

    @property
    def target(self) -> Target:
        raise NotImplementedError

    def run(
            self,
            circuit: QuantumCircuit,
            shots: int = None,
            qubit_mapping: dict[Qubit, str] = None
    ) -> 'qiskit_iqm.IQMJob':
        circuit_serialized = serialize_circuit(circuit)
        mapping_serialized = serialize_qubit_mapping(qubit_mapping or self.options.qubit_mapping, circuit)

        job_uuid = self._client.submit_circuit(circuit_serialized, mapping_serialized, shots=shots or self.options.shots)
        return qiskit_iqm.IQMJob(self, str(job_uuid))

    def retrieve_job(self, job_id: str):
        return qiskit_iqm.IQMJob(self, job_id)
