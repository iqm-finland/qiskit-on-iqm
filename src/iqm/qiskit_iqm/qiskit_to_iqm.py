# Copyright 2022-2025 Qiskit on IQM developers
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
from typing import Collection

import numpy as np
from qiskit import QuantumCircuit as QiskitQuantumCircuit
from qiskit.circuit import ClassicalRegister, Clbit, QuantumRegister
from qiskit.transpiler.layout import Layout

from iqm.iqm_client import Instruction
from iqm.qiskit_iqm.move_gate import MoveGate


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


def serialize_instructions(
    circuit: QiskitQuantumCircuit, qubit_index_to_name: dict[int, str], allowed_nonnative_gates: Collection[str] = ()
) -> list[Instruction]:
    """Serialize a quantum circuit into the IQM data transfer format.

    This is IQM's internal helper for :meth:`.IQMBackend.serialize_circuit` that gives slightly more control.
    See :meth:`.IQMBackend.serialize_circuit` for details.

    Args:
        circuit: quantum circuit to serialize
        qubit_index_to_name: Mapping from qubit indices to the corresponding qubit names.
        allowed_nonnative_gates: Names of gates that are converted as-is without validation.
            By default, any gate that can't be converted will raise an error.
            If such gates are present in the circuit, the caller must edit the result to be valid and executable.
            Notably, since IQM transfer format requires named parameters and qiskit parameters don't have names, the
            `i` th parameter of an unrecognized instruction is given the name ``"p<i>"``.

    Returns:
        list of instructions representing the circuit

    Raises:
        ValueError: circuit contains an unsupported instruction or is not transpiled in general
    """
    # pylint: disable=too-many-branches,too-many-statements
    instructions: list[Instruction] = []
    # maps clbits to the latest "measure" instruction to store its result there
    clbit_to_measure: dict[Clbit, Instruction] = {}
    for circuit_instruction in circuit.data:
        instruction = circuit_instruction.operation
        qubit_names = [qubit_index_to_name[circuit.find_bit(qubit).index] for qubit in circuit_instruction.qubits]
        if instruction.name == 'r':
            angle_t = float(instruction.params[0] / (2 * np.pi))
            phase_t = float(instruction.params[1] / (2 * np.pi))
            native_inst = Instruction(name='prx', qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': phase_t})
        elif instruction.name == 'x':
            native_inst = Instruction(name='prx', qubits=qubit_names, args={'angle_t': 0.5, 'phase_t': 0.0})
        elif instruction.name == 'rx':
            angle_t = float(instruction.params[0] / (2 * np.pi))
            native_inst = Instruction(name='prx', qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': 0.0})
        elif instruction.name == 'y':
            native_inst = Instruction(name='prx', qubits=qubit_names, args={'angle_t': 0.5, 'phase_t': 0.25})
        elif instruction.name == 'ry':
            angle_t = float(instruction.params[0] / (2 * np.pi))
            native_inst = Instruction(name='prx', qubits=qubit_names, args={'angle_t': angle_t, 'phase_t': 0.25})
        elif instruction.name == 'cz':
            native_inst = Instruction(name='cz', qubits=qubit_names, args={})
        elif instruction.name == 'move':
            native_inst = Instruction(name='move', qubits=qubit_names, args={})
        elif instruction.name == 'barrier':
            native_inst = Instruction(name='barrier', qubits=qubit_names, args={})
        elif instruction.name == 'delay':
            duration = float(instruction.params[0])
            # convert duration to seconds
            unit = instruction.unit
            if unit == 'dt':
                duration *= 1e-9  # we arbitrarily pick dt == 1 ns
            elif unit == 's':
                pass
            elif unit == 'ms':
                duration *= 1e-3
            elif unit == 'us':
                duration *= 1e-6
            elif unit == 'ns':
                duration *= 1e-9
            elif unit == 'ps':
                duration *= 1e-12
            else:
                raise ValueError(f"Delay: Unsupported unit '{unit}'")
            native_inst = Instruction(name='delay', qubits=qubit_names, args={'duration': duration})
        elif instruction.name == 'measure':
            if len(circuit_instruction.clbits) != 1:
                raise ValueError(
                    f'Unexpected: measurement instruction {circuit_instruction} uses multiple classical bits.'
                )
            clbit = circuit_instruction.clbits[0]  # always a single-qubit measurement
            mk = str(MeasurementKey.from_clbit(clbit, circuit))
            native_inst = Instruction(name='measure', qubits=qubit_names, args={'key': mk})
            clbit_to_measure[clbit] = native_inst
        elif instruction.name == 'reset':
            native_inst = Instruction(name='reset', qubits=qubit_names, args={})
        elif instruction.name == 'id':
            continue
        elif instruction.name in allowed_nonnative_gates:
            args = {f'p{i}': param for i, param in enumerate(instruction.params)}
            native_inst = Instruction.model_construct(name=instruction.name, qubits=tuple(qubit_names), args=args)
        else:
            raise ValueError(
                f"Instruction '{instruction.name}' in the circuit '{circuit.name}' is not natively supported. "
                f'You need to transpile the circuit before execution.'
            )

        # classically controlled gates (using the c_if method)
        # TODO we do not check anywhere if cc_prx is available for this locus!
        condition = instruction.condition
        if condition is not None:
            if native_inst.name != 'prx':
                raise ValueError(
                    'This backend only supports conditionals on r, x, y, rx and ry gates,' f' not on {instruction.name}'
                )
            native_inst.name = 'cc_prx'
            creg, value = condition
            if isinstance(creg, ClassicalRegister):
                if len(creg) != 1:
                    raise ValueError(f'{instruction} is conditioned on multiple bits, this is not supported.')
                if value != 1:
                    raise ValueError(
                        f'{instruction} is conditioned on integer value {value}, only value 1 is supported.'
                    )
                clbit = creg[0]
            else:
                clbit = creg  # it is a Clbit

            # Set up feedback routing.
            # The latest "measure" instruction to write to that classical bit is modified, it is
            # given an explicit feedback_key equal to its measurement key.
            # The same feedback_key is given to the controlled instruction, along with the feedback qubit.
            measure_inst = clbit_to_measure[clbit]
            feedback_key = measure_inst.args['key']
            measure_inst.args['feedback_key'] = feedback_key  # this measure is used to provide feedback
            physical_qubit_name = measure_inst.qubits[0]  # single-qubit measurement
            native_inst.args['feedback_key'] = feedback_key
            native_inst.args['feedback_qubit'] = physical_qubit_name

        instructions.append(native_inst)
    return instructions


# pylint: disable=too-many-branches
def deserialize_instructions(
    instructions: list[Instruction], qubit_name_to_index: dict[str, int], layout: Layout
) -> QiskitQuantumCircuit:
    """Helper function to turn a list of IQM Instructions into a Qiskit QuantumCircuit.

    Args:
        instructions: The gates in the circuit.
        qubit_name_to_index: Mapping from qubit names to their indices, as specified in a backend.
        layout: Qiskit representation of a layout.

    Raises:
        ValueError: Thrown when a given instruction is not supported.

    Returns:
        Qiskit circuit represented by the given instructions.
    """
    # maps measurement key to the corresponding clbit
    mk_to_clbit: dict[str, Clbit] = {}
    # maps feedback key to the corresponding clbit
    fk_to_clbit: dict[str, Clbit] = {}

    # maps creg index to creg in the circuit
    cl_regs: dict[int, ClassicalRegister] = {}

    def register_key(key: str, mapping: dict[str, Clbit]) -> None:
        """Update the classical registers and the given key-to-clbit mapping with the given key."""
        mk = MeasurementKey.from_string(key)
        # find/create the corresponding creg
        creg = cl_regs.setdefault(mk.creg_idx, ClassicalRegister(size=mk.creg_len, name=mk.creg_name))
        # add the key to the given mapping
        if mk.clbit_idx < len(creg):
            mapping[str(mk)] = creg[mk.clbit_idx]
        else:
            raise IndexError(f'{mk}: Clbit index {mk.clbit_idx} is out of range for {creg}.')

    for instr in instructions:
        if instr.name == 'measure':
            register_key(instr.args['key'], mk_to_clbit)
            if (key := instr.args.get('feedback_key')) is not None:
                register_key(key, fk_to_clbit)

    # Add resonators
    n_qubits = len(layout.get_physical_bits())
    n_resonators = len(qubit_name_to_index) - n_qubits
    if n_resonators > 0:
        new_qreg = QuantumRegister(n_resonators, 'resonators')
        layout.add_register(new_qreg)
        for idx in range(n_resonators):
            layout.add(new_qreg[idx], idx + n_qubits)
    index_to_qiskit_qubit = layout.get_physical_bits()
    # Add an empty Classical register when the original circuit had unused classical registers
    circuit = QiskitQuantumCircuit(
        *layout.get_registers(),
        *(cl_regs.get(i, ClassicalRegister(0)) for i in range(max(cl_regs) + 1 if cl_regs else 0)),
    )
    for instr in instructions:
        locus = [index_to_qiskit_qubit[qubit_name_to_index[q]] for q in instr.qubits]
        if instr.name == 'prx':
            angle_t = instr.args['angle_t'] * 2 * np.pi
            phase_t = instr.args['phase_t'] * 2 * np.pi
            circuit.r(angle_t, phase_t, locus[0])
        elif instr.name == 'cz':
            circuit.cz(*locus)
        elif instr.name == 'move':
            circuit.append(MoveGate(), locus)
        elif instr.name == 'measure':
            mk = MeasurementKey.from_string(instr.args['key'])
            circuit.measure(locus[0], mk_to_clbit[str(mk)])
        elif instr.name == 'barrier':
            circuit.barrier(*locus)
        elif instr.name == 'delay':
            duration = instr.args['duration']
            circuit.delay(duration, locus, unit='s')  # native delay instructions always use seconds
        elif instr.name == 'cc_prx':
            angle_t = instr.args['angle_t'] * 2 * np.pi
            phase_t = instr.args['phase_t'] * 2 * np.pi
            feedback_key = instr.args['feedback_key']
            # NOTE: 'feedback_qubit' is not needed, because in Qiskit you only have single-qubit measurements.
            circuit.r(angle_t, phase_t, locus[0]).c_if(fk_to_clbit[feedback_key], 1)
        elif instr.name == 'reset':
            for qubit in locus:
                circuit.reset(qubit)
        else:
            raise ValueError(f'Unsupported instruction {instr.name} in the circuit.')
    return circuit
