# Copyright 2022-2023 Qiskit on IQM developers
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

import re
from typing import Optional, Union

from iqm_client import Circuit, Instruction, IQMClient
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, Measure, RGate
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target

from qiskit_iqm.iqm_job import IQMJob
from qiskit_iqm.qiskit_to_iqm import MeasurementKey


class IQMBackend(BackendV2):
    """Qiskit backend enabling the execution of quantum circuits on IQM quantum computers.

    Args:
        client: IQM client instance for submitting circuits for execution on an IQM server
        **kwargs: optional arguments to be passed to the parent Qiskit Backend initializer
    """

    def __init__(self, client: IQMClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

        arch = client.get_quantum_architecture()

        def get_num_or_zero(name: str) -> int:
            match = re.search(r'(\d+)', name)
            return int(match.group(1)) if match else 0

        qb_to_idx = {qb: idx for idx, qb in enumerate(sorted(arch.qubits, key=get_num_or_zero))}

        target = Target()
        # There is no dedicated direct way of setting just the qubit connectivity and the native gates to the target.
        # Such info is automatically deduced once all instruction properties are set. Currently, we do not retrieve
        # any properties from the server, and we are interested only in letting the target know what is the native gate
        # set and the connectivity of the device under use. Thus, we populate the target with None properties.
        target.add_instruction(
            RGate(Parameter('theta'), Parameter('phi')), {(qb_to_idx[qb],): None for qb in arch.qubits}
        )
        target.add_instruction(
            CZGate(), {(qb_to_idx[qb1], qb_to_idx[qb2]): None for qb1, qb2 in arch.qubit_connectivity}
        )
        target.add_instruction(Measure(), {(qb_to_idx[qb],): None for qb in arch.qubits})

        self._target = target
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1024, calibration_set_id=None)

    @property
    def target(self) -> Target:
        return self._target

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

        circuits_serialized: list[Circuit] = [self.serialize_circuit(circuit) for circuit in circuits]
        qubit_mapping = {str(idx): qb for idx, qb in self._idx_to_qb.items()}
        uuid = self.client.submit_circuits(
            circuits_serialized, qubit_mapping=qubit_mapping, calibration_set_id=calibration_set_id, shots=shots
        )
        job = IQMJob(self, str(uuid), shots=shots)
        job.circuit_metadata = [c.metadata for c in circuits]
        return job

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id."""
        return IQMJob(self, job_id)

    def close_client(self):
        """Close IQMClient's session with the authentication server. Discard the client."""
        if self.client is not None:
            self.client.close_auth_session()
        self.client = None

    def qubit_name_to_index(self, name: str) -> Optional[int]:
        """Given an IQM-style qubit name ('QB1', 'QB2', etc.) return the corresponding index in the register. Returns
        None is the given name does not belong to the backend."""
        return self._qb_to_idx.get(name)

    def index_to_qubit_name(self, index: int) -> Optional[str]:
        """Given an index in the backend register return the corresponding IQM-style qubit name ('QB1', 'QB2', etc.).
        Returns None if the given index does not correspond to any qubit in the backend."""
        return self._idx_to_qb.get(index)

    def serialize_circuit(self, circuit: QuantumCircuit) -> Circuit:
        """Serialize a quantum circuit into the IQM data transfer format.

        Qiskit uses one measurement instruction per qubit (i.e. there is no measurement grouping concept). While
        serializing we do not group any measurements together but rather associate a unique measurement key with each
        measurement instruction, so that the results can later be reconstructed correctly (see :class:`MeasurementKey`
        documentation for more details).

        Args:
            circuit: quantum circuit to serialize

        Returns:
            data transfer object representing the circuit

        Raises:
            ValueError: circuit contains an unsupported instruction or is not transpiled in general
        """
        if len(circuit.qregs) != 1 or len(circuit.qregs[0]) != self.num_qubits:
            raise ValueError(
                f"The circuit '{circuit.name}' does not contain a single quantum register of length {self.num_qubits}, "
                f'which indicates that it has not been transpiled against the current backend.'
            )
        instructions = []
        for instruction, qubits, clbits in circuit.data:
            qubit_names = [str(circuit.find_bit(qubit).index) for qubit in qubits]
            if instruction.name == 'r':
                angle_t = float(instruction.params[0] / (2 * np.pi))
                phase_t = float(instruction.params[1] / (2 * np.pi))
                instructions.append(
                    Instruction(name='phased_rx', qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': phase_t})
                )
            elif instruction.name == 'cz':
                instructions.append(Instruction(name='cz', qubits=qubit_names, args={}))
            elif instruction.name == 'barrier':
                instructions.append(Instruction(name='barrier', qubits=qubit_names, args={}))
            elif instruction.name == 'measure':
                mk = MeasurementKey.from_clbit(clbits[0], circuit)
                instructions.append(Instruction(name='measurement', qubits=qubit_names, args={'key': str(mk)}))
            else:
                raise ValueError(
                    f"Instruction '{instruction.name}' in the circuit '{circuit.name}' is not natively supported. "
                    f'You need to transpile the circuit before execution.'
                )

        return Circuit(name=circuit.name, instructions=instructions, metadata=circuit.metadata)
