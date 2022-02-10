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
from typing import List
import numpy as np

from qiskit.circuit import Instruction as QiskitInstruction, Qubit, Clbit
from iqm_client.iqm_client import Instruction


class InstructionNotSupportedError(RuntimeError):
    """Raised when a given operation is not supported by the IQM server."""


def map_instruction(instruction: QiskitInstruction, qubits: List[Qubit], cbits: List[Clbit]) -> Instruction:
    """Map a Qiskit Instruction to the IQM data transfer format.

    Assumes the circuit has been transpiled so that it only contains operations natively supported by the
    given IQM quantum architecture.

    Args:
        instruction: The qiskit instruction to map
        qubits: List of qubits that the instruction acts on or works with
        cbits: List of classical bits that the instruction acts on or works with

    Returns:
        `iqm_client.iqm_client.Instruction`: the converted operation

    Raises:
        `~OperationNotSupportedError` When the circuit contains an unsupported operation.

    """
    qubit_names = [qubit.register.name + str(qubit.index) for qubit in qubits]
    creg_names = [bit.register.name + str(bit.index) for bit in cbits]
    phased_rx_name = 'phased_rx'
    # TODO, num_qubits > n for n qubit operations
    if instruction.name == 'r':
        angle_t = instruction.params[0] / (2*np.pi)
        phase_t = instruction.params[1] / (2*np.pi)
        return Instruction(name=phased_rx_name, qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': phase_t})
    if instruction.name == 'cz':
        return Instruction(name='cz', qubits=qubit_names, args={})
    elif instruction.name == 'measure':
        return Instruction(name='measurement', qubits=qubit_names, args={'key': creg_names[0]})
    else:
        raise InstructionNotSupportedError(f'Instruction {instruction.name} not natively supported.')
