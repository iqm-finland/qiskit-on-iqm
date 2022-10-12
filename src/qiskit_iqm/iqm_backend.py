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
from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, Measure, RGate
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import InstructionProperties, Target

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
        return Options(shots=1024, calibration_set_id=None)

    @property
    def target(self) -> Target:
        adonis_target = Target()

        theta = Parameter('theta')
        phi = Parameter('phi')

        # No properties, just list the qubits that support phased_rx and measurement, i.e. all qubits
        single_qubit_properties = {
            (0,): InstructionProperties(),  # QB1
            (1,): InstructionProperties(),  # QB2
            (2,): InstructionProperties(),  # QB3
            (3,): InstructionProperties(),  # QB4
            (4,): InstructionProperties(),  # QB5
        }
        adonis_target.add_instruction(RGate(theta, phi), single_qubit_properties)
        adonis_target.add_instruction(Measure(), single_qubit_properties)

        # Again, no properties, just list the connectivity
        cz_properties = {
            (0, 2): InstructionProperties(),  # QB1 - QB3
            (2, 0): InstructionProperties(),  # reverse direction
            (1, 2): InstructionProperties(),  # QB2 - QB3
            (2, 1): InstructionProperties(),  # reverse direction
            (3, 2): InstructionProperties(),  # QB4 - QB3
            (2, 3): InstructionProperties(),  # reverse direction
            (4, 2): InstructionProperties(),  # QB5 - QB3
            (2, 4): InstructionProperties(),  # reverse direction
        }
        adonis_target.add_instruction(CZGate(), cz_properties)
        return adonis_target

    @property
    def max_circuits(self) -> Optional[int]:
        return None

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> IQMJob:
        if self.client is None:
            raise RuntimeError('Session to IQM client has been closed.')

        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError('Empty list of circuits submitted for execution.')

        shots = options.get('shots', self.options.shots)
        calibration_set_id = options.get('calibration_set_id', self.options.calibration_set_id)

        qubit_mappings = []
        for circuit in circuits:
            if not circuit._layout and (len(circuit.qregs) != 1 or len(circuit.qregs[0]) != 5):
                raise ValueError('Circuit should either be transpiled or shall contain exactly one quantum register of '
                                 'length 5, in which case it will be assumed that qubit at index i corresponds to QB{i+1}.')
            qm = qubit_mapping_with_names(dict(zip(circuit.qubits, ['QB1', 'QB2', 'QB3', 'QB4', 'QB5'])), circuit)
            qubit_mappings.append(qm)

        circuits_serialized = [serialize_circuit(circuit) for circuit in circuits]
        uuid = self.client.submit_circuits(circuits_serialized,
                                           qubit_mappings=qubit_mappings,
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
