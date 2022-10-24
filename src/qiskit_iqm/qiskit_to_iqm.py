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

from dataclasses import dataclass
import re

from qiskit import QuantumCircuit as QiskitQuantumCircuit
from qiskit.circuit import Clbit


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
        """Create a MeasurementKey from its string representation."""
        match = re.match(r'^(.*)_(\d+)_(\d+)_(\d+)$', string)
        if match is None:
            raise ValueError('Invalid measurement key string representation.')
        return cls(match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)))

    @classmethod
    def from_clbit(cls, clbit: Clbit, circuit: QiskitQuantumCircuit) -> MeasurementKey:
        """Create a MeasurementKey for a classical bit in a quantum circuit."""
        bitloc = circuit.find_bit(clbit)
        creg = bitloc.registers[0][0]
        creg_idx = circuit.cregs.index(creg)
        clbit_idx = bitloc.registers[0][1]
        return cls(creg.name, len(creg), creg_idx, clbit_idx)
