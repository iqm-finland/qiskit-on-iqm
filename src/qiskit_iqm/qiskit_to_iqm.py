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
"""Conversion tools from Qiskit to IQM representation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from iqm_client.iqm_client import Circuit, Instruction, SingleQubitMapping
from qiskit import QuantumCircuit as QiskitQuantumCircuit
from qiskit.circuit import Clbit, Qubit


class InstructionNotSupportedError(RuntimeError):
    """Raised when a given instruction is not supported by the IQM server."""


@dataclass(frozen=True)
class MeasurementKey:
    """Unique key associated with a measurement instruction.

    Qiskit stores the results of quantum measurements in classical registers consisting of bits.
    The circuit execution results are presented as bitstrings of a certain structure so that the classical
    register and the index within that register for each bit is implied from its position in the bitstring.

    For example, if you have two classical registers in the circuit with lengths 3 and 2, then the
    measurement results will look like '01 101' if the classical register of length 3 was added to
    the circuit first, and '101 01' otherwise. If a bit in a classical register is not used in any
    measurement operation it will still show up in the results with the default value of '0'.

    To be able to handle measurement results in a Qiskit-friendly way, we need to keep around some
    information about how the circuit was constructed. This can, for example, be achieved by keeping
    around the original Qiskit quantum circuit and using it when constructing the results in
    :class:`.IQMJob`. This should be done so that the circuit is saved on the server side and not in
    ``IQMJob``, since otherwise users will not be able to retrieve results from a detached Python
    environment solely based on the job id. Another option is to use measurement key strings to
    store the required info. Qiskit does not use measurement keys, so we are free to use them
    internally in the communication with the IQM server, and can encode the necessary information in
    them.

    This class encapsulates the necessary info, and provides methods to transform between this
    representation and the measurement key string representation.

    Args:
        creg_name: name of the classical register
        creg_len: number of bits in the classical register
        creg_idx: Index of the classical register in the circuit. Determines the order in which this register was added
            to the circuit relative to the others.
        clbit_idx: index of the classical bit within the classical register
    """
    creg_name: str
    creg_len: int
    creg_idx: int
    clbit_idx: int

    def __str__(self):
        return f'{self.creg_name}_{self.creg_len}_{self.creg_idx}_{self.clbit_idx}'

    @classmethod
    def from_string(cls, string: str) -> MeasurementKey:
        """Create a MeasurementKey from its string representation.
        """
        match = re.match(r'^(.*)_(\d+)_(\d+)_(\d+)$', string)
        return cls(match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)))

    @classmethod
    def from_clbit(cls, clbit: Clbit, circuit: QiskitQuantumCircuit) -> MeasurementKey:
        """Create a MeasurementKey for a classical bit in a quantum circuit.
        """
        bitloc = circuit.find_bit(clbit)
        creg = bitloc.registers[0][0]
        creg_idx = circuit.cregs.index(creg)
        clbit_idx = bitloc.registers[0][1]
        return cls(creg.name, len(creg), creg_idx, clbit_idx)


def qubit_to_name(qubit: Qubit, circuit: QiskitQuantumCircuit) -> str:
    """Construct a unique name for a qubit based on its index in the circuit.

    Args:
        qubit: logical qubit
        circuit: circuit the qubit belongs to

    Returns:
        logical qubit name
    """
    return f'qubit_{circuit.find_bit(qubit).index}'


def serialize_qubit_mapping(qubit_mapping: dict[Qubit, str], circuit: QiskitQuantumCircuit) -> list[SingleQubitMapping]:
    """Serialize a qubit mapping into the IQM data transfer format.

    Args:
        qubit_mapping: mapping from logical qubits in the circuit to physical qubit names
        circuit: quantum circuit containing the logical qubits

    Returns:
        data transfer object representing the qubit mapping
    """
    return [
        SingleQubitMapping(logical_name=qubit_to_name(k, circuit), physical_name=v) for k, v in qubit_mapping.items()
    ]


def serialize_circuit(circuit: QiskitQuantumCircuit) -> Circuit:
    """Serialize a quantum circuit into the IQM data transfer format.

    Assumes that ``circuit`` has been transpiled so that it only contains operations natively supported by the
    given IQM quantum architecture.

    Qiskit uses one measurement instruction per qubit (i.e. there are no multi-qubit measurement instructions).
    While serializing we do not group any measurements together but rather associate a unique measurement key with each
    measurement instruction, so that the results can later be reconstructed correctly (see :class:`MeasurementKey`
    documentation for more details).

    Args:
        circuit: quantum circuit to serialize

    Returns:
        data transfer object representing the circuit

    Raises:
        InstructionNotSupportedError: circuit contains an unsupported instruction
    """
    instructions = []
    for instruction, qubits, clbits in circuit.data:
        qubit_names = [qubit_to_name(qubit, circuit) for qubit in qubits]
        if instruction.name == 'r':
            angle_t = float(instruction.params[0] / (2 * np.pi))
            phase_t = float(instruction.params[1] / (2 * np.pi))
            instructions.append(
                Instruction(name='phased_rx', qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': phase_t})
            )
        elif instruction.name == 'cz':
            instructions.append(Instruction(name='cz', qubits=qubit_names, args={}))
        elif instruction.name == 'measure':
            mk = MeasurementKey.from_clbit(clbits[0], circuit)
            instructions.append(Instruction(name='measurement', qubits=qubit_names, args={'key': str(mk)}))
        else:
            raise InstructionNotSupportedError(f'Instruction {instruction.name} not natively supported.')

    return Circuit(name='Serialized from Qiskit', instructions=instructions)
