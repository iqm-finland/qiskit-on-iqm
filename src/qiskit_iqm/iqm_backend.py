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
from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, Measure, RGate
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import InstructionProperties, Target

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
    def max_circuits(self) -> int:
        return 1

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> IQMJob:
        if isinstance(run_input, list) and len(run_input) > 1:
            raise ValueError('IQM backend currently does not support execution of multiple circuits at once.')
        circuit = run_input if isinstance(run_input, QuantumCircuit) else run_input[0]

        shots = options.get('shots', self.options.shots)

        if not circuit._layout and (len(circuit.qregs) != 1 or len(circuit.qregs[0]) != 5):
            raise ValueError('Circuit should either be transpiled or shall contain exactly one quantum register of '
                             'length 5, in which case it will be assumed that qubit at index i corresponds to QB{i+1}.')
        qubit_mapping = dict(zip(circuit.qubits, ['QB1', 'QB2', 'QB3', 'QB4', 'QB5']))
        circuit_serialized = serialize_circuit(circuit)
        mapping_serialized = serialize_qubit_mapping(qubit_mapping, circuit)

        uuid = self.client.submit_circuit(circuit_serialized, mapping_serialized, shots=shots)
        print(f'job id: {str(uuid)}')
        job = IQMJob(self, str(uuid), shots=shots)
        # FIXME: monkeypatch the job object with metadata from circuit (needed for quantum volume experiments)
        job.circuit_metadata = circuit.metadata
        return job

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id.
        """
        return IQMJob(self, job_id)
