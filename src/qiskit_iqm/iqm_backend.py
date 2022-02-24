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
"""Qiskit backend for IQM quantum computers.
"""
from __future__ import annotations

from typing import Union

from iqm_client.iqm_client import IQMClient
from qiskit import QuantumCircuit
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target

from qiskit_iqm.iqm_job import IQMJob
from qiskit_iqm.qiskit_to_iqm import serialize_circuit, serialize_qubit_mapping


class IQMBackend(BackendV2):
    """Qiskit backend enabling the execution of quantum circuits on IQM quantum computers.

    Args:
        client: IQM Cortex client used for submitting circuits for execution on an IQM server
        **kwargs: optional arguments to be passed to the parent Qiskit Backend initializer
    """
    def __init__(self, client: IQMClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1024, qubit_mapping=None)

    @property
    def target(self) -> Target:
        raise NotImplementedError

    @property
    def max_circuits(self) -> int:
        return 1

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> IQMJob:
        if isinstance(run_input, list) and len(run_input) > 1:
            raise ValueError('IQM backend currently does not support execution of multiple circuits at once.')
        circuit = run_input if isinstance(run_input, QuantumCircuit) else run_input[0]

        qubit_mapping = options.get('qubit_mapping', self.options.qubit_mapping)
        shots = options.get('shots', self.options.shots)

        circuit_serialized = serialize_circuit(circuit)
        mapping_serialized = serialize_qubit_mapping(qubit_mapping, circuit)

        uuid = self.client.submit_circuit(circuit_serialized, mapping_serialized, shots=shots)
        return IQMJob(self, str(uuid), shots=shots)

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id.
        """
        return IQMJob(self, job_id)
