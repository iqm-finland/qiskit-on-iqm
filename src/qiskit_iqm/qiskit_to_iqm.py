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
Serialize various objects into IQM data transfer format.
"""
from iqm_client.iqm_client import Circuit, Instruction, SingleQubitMapping
import numpy as np
from qiskit import QuantumCircuit as QiskitQuantumCircuit
from qiskit.circuit import Qubit


class InstructionNotSupportedError(RuntimeError):
    """Raised when a given instruction is not supported by the IQM server."""


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

    Args:
        circuit: quantum circuit to serialize

    Returns:
        Data transfer object representing the circuit

    Raises:
        `~InstructionNotSupportedError` When the circuit contains an unsupported instruction.
    """
    instructions = []
    measured_qubits = []
    for instruction, qubits, _ in circuit.data:
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
            measured_qubits.extend(qubit_names)
        else:
            raise InstructionNotSupportedError(f'Instruction {instruction.name} not natively supported.')

    instructions.append(Instruction(name='measurement', qubits=measured_qubits, args={'key': 'mk'}))
    return Circuit(name='Serialized from Qiskit', instructions=instructions)
