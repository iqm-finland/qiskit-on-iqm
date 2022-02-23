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
Various conversion tools from Qiskit to IQM representation.
"""
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
    """Instances of this class define a unique key associated with each measurement instruction.

    In Qiskit, the circuit execution results are presented as bitstrings of certain structure so that the classical
    register and the index within the register for each bit is implied from its position in the bitstring. For example
    if you have two classical registers in the circuit with lengths 3 and 2, then the measurement results will look like
    '01 101' if the classical register of length 3 was added to the circuit first, and '101 01' otherwise. If a
    classical bit in a classical register is not used in any measurement operation it will still show up in the results
    with default value of 0. To be able to construct measurement results in a Qiskit friendly way as much as possible,
    we need to keep around some information about how the circuit was constructed. This can, for example, be achieved
    by keeping around the original Qiskit quantum circuit and using it when constructing results in IQMJob. This should
    be done so that the circuit is saved on server side and not in IQMJob, otherwise users will not be able to retrieve
    results from a detached python environment solely based on job id. Another option is to use measurement keys to
    encode the required info. Qiskit does not use measurement keys, so we are free to use them internally in the
    communication with IQM server, and we can generate whatever measurement keys that contain necessary information.
    This class basically encapsulates the necessary info and provides functions to construct to and reconstruct from
    unique measurement key strings.

    Args:
        creg_name: Name of the classical register.
        creg_len: Length of the classical register.
        creg_idx: Index of the classical register in the circuit. Determines the order in which this register was added
                  to the circuit relative to the other ones.
        clbit_idx: Index of the classical bit within the classical register.
    """
    creg_name: str
    creg_len: int
    creg_idx: int
    clbit_idx: int

    def __str__(self):
        return f'{self.creg_name}_{self.creg_len}_{self.creg_idx}_{self.clbit_idx}'

    @classmethod
    def from_string(cls, string: str):
        """Create a MeasurementKey instance from string representation."""
        match = re.match(r'^(.*)_(\d+)_(\d+)_(\d+)$', string)
        return cls(match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)))

    @classmethod
    def from_circuit(cls, circuit: QiskitQuantumCircuit, clbit: Clbit):
        """Create a MeasurementKey instance based on information available in quantum circuit"""
        bitloc = circuit.find_bit(clbit)
        creg_idx = circuit.cregs.index(bitloc.registers[0][0])
        clbit_idx = bitloc.registers[0][1]
        return cls(bitloc.registers[0][0].name, len(bitloc.registers[0][0]), creg_idx, clbit_idx)


def qubit_to_name(qubit: Qubit, circuit: QiskitQuantumCircuit) -> str:
    """Construct a unique qubit name based on its index in the circuit.

    Args:
        qubit: A qubit.
        circuit: Circuit the qubit belongs to.

    Returns:
        The constructed qubit name.
    """
    return f'Qubit_{circuit.find_bit(qubit).index}'


def serialize_qubit_mapping(qubit_mapping: dict[Qubit, str], circuit: QiskitQuantumCircuit) -> list[SingleQubitMapping]:
    """Serialize qubit mapping into IQM data transfer format.

    Args:
        qubit_mapping: Mapping from virtual qubits in the circuit to physical qubit names.
        circuit: Quantum circuit.

    Returns:
        Data transfer object representing the qubit mapping.
    """
    return \
        [SingleQubitMapping(logical_name=qubit_to_name(k, circuit), physical_name=v) for k, v in qubit_mapping.items()]


def serialize_circuit(circuit: QiskitQuantumCircuit) -> Circuit:
    """Serializes a quantum circuit into the IQM data transfer format.

    Assumes the circuit has been transpiled so that it only contains operations natively supported by the
    given IQM quantum architecture.
    Qiskit uses one measurement gate per qubit, and does not use measurement key/identifiers. The bitstrings in the
    circuit execution results have bits from left to right corresponding to the order in which the measurements were
    added. While serializing we collect all measurements in the order they appear and add one measurement operation,
    with measurement key 'mk'.

    Args:
        circuit: quantum circuit to serialize

    Returns:
        Data transfer object representing the circuit

    Raises:
        `InstructionNotSupportedError` When the circuit contains an unsupported instruction.
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
            mk = MeasurementKey.from_circuit(circuit, clbits[0])
            instructions.append(Instruction(name='measurement', qubits=qubit_names, args={'key': str(mk)}))
        else:
            raise InstructionNotSupportedError(f'Instruction {instruction.name} not natively supported.')

    return Circuit(name='Serialized from Qiskit', instructions=instructions)
