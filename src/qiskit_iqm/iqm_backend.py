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

from typing import Optional, Union

from iqm_client import IQMClient
from qiskit import QuantumCircuit
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target

from qiskit_iqm.iqm_job import IQMJob
from qiskit_iqm.qiskit_to_iqm import (qubit_mapping_with_names,
                                      serialize_circuit)


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
        return Options(shots=1024, qubit_mapping=None, settings=None, calibration_set_id=None)

    @property
    def target(self) -> Target:
        raise NotImplementedError

    @property
    def max_circuits(self) -> Optional[int]:
        return None

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> IQMJob:
        if self.client is None:
            raise RuntimeError('Session to IQM client has been closed.')

        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError('Empty list of circuits submitted for execution.')

        qubit_mapping = options.get('qubit_mapping', self.options.qubit_mapping)
        shots = options.get('shots', self.options.shots)
        settings = options.get('settings', self.options.settings)
        calibration_set_id = options.get('calibration_set_id', self.options.calibration_set_id)

        if qubit_mapping is not None:
            # process qubit mapping for each circuit separately
            mappings = [
                qubit_mapping_with_names(qubit_mapping, circuit)
                for circuit in circuits
            ]
            # Check that all resulted into the same mapping, otherwise raise error
            if any(mapping != mappings[0] for mapping in mappings):
                raise ValueError("""All circuits must use the same qubit mapping. This error might have
                occurred by providing circuits that were not generated from a parameterized circuit.""")
            qubit_mapping = mappings[0]

        circuits_serialized = [serialize_circuit(circuit) for circuit in circuits]
        uuid = self.client.submit_circuits(circuits_serialized,
                                           qubit_mapping=qubit_mapping,
                                           settings=settings,
                                           calibration_set_id=calibration_set_id,
                                           shots=shots)
        return IQMJob(self, str(uuid), shots=shots)

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id.
        """
        return IQMJob(self, job_id)

    def close_client(self):
        """Close IQMClient's session with the authentication server. Discard the client."""
        if self.client is not None:
            self.client.close_auth_session()
        self.client = None
