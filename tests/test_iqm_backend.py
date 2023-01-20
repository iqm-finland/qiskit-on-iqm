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

"""Testing IQM backend.
"""
from numbers import Number
import uuid

from iqm_client import IQMClient
from mockito import mock, patch, when
import numpy as np
import pytest
from qiskit import QuantumCircuit, execute
from qiskit.circuit import Parameter, ParameterExpression
from qiskit.circuit.library import RGate
from qiskit.compiler import transpile

from qiskit_iqm import IQMBackend, IQMJob


@pytest.fixture
def backend(linear_architecture_3q):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(linear_architecture_3q)
    return IQMBackend(client)


@pytest.fixture
def qubit_mapping():
    return {'0': 'QB1', '1': 'QB2', '2': 'QB3'}


@pytest.fixture
def circuit():
    return QuantumCircuit(3, 3)


def test_default_options(backend):
    assert backend.options.shots == 1024
    assert backend.options.calibration_set_id is None


def test_retrieve_job(backend):
    job = backend.retrieve_job('a job id')
    assert job.backend() == backend
    assert job.job_id() == 'a job id'


def test_max_circuits(backend):
    assert backend.max_circuits is None


def test_qubit_name_to_index_to_qubit_name(adonis_architecture_shuffled_names):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(adonis_architecture_shuffled_names)
    backend = IQMBackend(client)

    correct_idx_name_associations = set(enumerate(['QB1', 'QB2', 'QB3', 'QB4', 'QB5']))
    assert all(backend.index_to_qubit_name(idx) == name for idx, name in correct_idx_name_associations)
    assert all(backend.qubit_name_to_index(name) == idx for idx, name in correct_idx_name_associations)

    assert backend.index_to_qubit_name(7) is None
    assert backend.qubit_name_to_index('Alice') is None


def test_serialize_circuit_raises_error_for_non_transpiled_circuit(backend, circuit):
    circuit = QuantumCircuit(2, 2)
    with pytest.raises(ValueError, match='has not been transpiled against the current backend'):
        backend.serialize_circuit(circuit)


def test_serialize_circuit_raises_error_for_unsupported_instruction(backend, circuit):
    circuit.sx(0)
    with pytest.raises(ValueError, match=f"Instruction 'sx' in the circuit '{circuit.name}' is not natively supported"):
        backend.serialize_circuit(circuit)


@pytest.mark.parametrize(
    'gate, expected_angle, expected_phase',
    [
        (RGate(theta=np.pi, phi=0), 1 / 2, 0),
        (RGate(theta=0, phi=np.pi), 0, 1 / 2),
        (RGate(theta=0, phi=2 * np.pi), 0, 1),
        (RGate(theta=2 * np.pi, phi=np.pi), 1, 1 / 2),
    ],
)
def test_serialize_circuit_maps_r_gate(circuit, gate, expected_angle, expected_phase, backend):
    circuit.append(gate, [0])
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    instr = circuit_ser.instructions[0]
    assert instr.name == 'phased_rx'
    assert instr.qubits == ('0',)
    # Serialized angles should be in full turns
    assert instr.args['angle_t'] == expected_angle
    assert instr.args['phase_t'] == expected_phase


def test_serialize_handles_parameter_expressions(circuit, backend):
    theta = Parameter('θ')
    phi = Parameter('φ')
    circuit.r(theta, phi, 0)
    circuit_bound = circuit.bind_parameters({theta: np.pi, phi: 0})

    # First make sure that circuit_bound does indeed represent parameters as ParameterExpression
    assert len(circuit_bound.data) == 1
    instruction = circuit_bound.data[0][0]
    assert all(isinstance(param, ParameterExpression) for param in instruction.params)

    # Now check that serialization correctly handles ParameterExpression
    circuit_ser = backend.serialize_circuit(circuit_bound)
    assert len(circuit_ser.instructions) == 1
    iqm_instruction = circuit_ser.instructions[0]
    assert isinstance(iqm_instruction.args['angle_t'], Number)
    assert isinstance(iqm_instruction.args['phase_t'], Number)


def test_serialize_circuit_maps_cz_gate(circuit, backend):
    circuit.cz(0, 2)
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'cz'
    assert circuit_ser.instructions[0].qubits == ('0', '2')
    assert circuit_ser.instructions[0].args == {}


def test_serialize_circuit_maps_individual_measurements(circuit, backend):
    circuit.measure(0, 0)
    circuit.measure(1, 1)
    circuit.measure(2, 2)
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 3
    for i, instruction in enumerate(circuit_ser.instructions):
        assert instruction.name == 'measurement'
        assert instruction.qubits == (f'{i}',)
        assert instruction.args == {'key': f'c_3_0_{i}'}


def test_serialize_circuit_batch_measurement(circuit, backend):
    circuit.measure([0, 1, 2], [0, 1, 2])
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 3
    for i, instruction in enumerate(circuit_ser.instructions):
        assert instruction.name == 'measurement'
        assert instruction.qubits == (f'{i}',)
        assert instruction.args == {'key': f'c_3_0_{i}'}


def test_serialize_circuit_barrier(circuit, backend):
    circuit.r(theta=np.pi, phi=0, qubit=0)
    circuit.barrier([0, 1])
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 2
    assert circuit_ser.instructions[1].name == 'barrier'
    assert circuit_ser.instructions[1].qubits == ('0', '1')
    assert circuit_ser.instructions[1].args == {}


def test_transpile(backend, circuit):
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 0)

    circuit_transpiled = transpile(circuit, backend=backend)
    cmap = backend.coupling_map.get_edges()
    for instruction, qubits, _ in circuit_transpiled.data:
        assert instruction.name in ('r', 'cz')
        if instruction.name == 'cz':
            idx1 = circuit_transpiled.find_bit(qubits[0]).index
            idx2 = circuit_transpiled.find_bit(qubits[1]).index
            assert ((idx1, idx2) in cmap) or ((idx2, idx1) in cmap)


def test_run_non_native_circuit_with_the_execute_function(backend, circuit):
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 2)

    some_id = uuid.uuid4()
    backend.client.submit_circuits = lambda *args, **kwargs: some_id
    job = execute(circuit, backend=backend, optimization_level=0)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_run_gets_options_from_execute_function(backend, circuit):
    """Test that any additional keyword arguments to the `execute` function are passed to `IQMBackend.run`. This is more
    of a test for Qiskit's `execute` function itself, but still good to have it here to know that the use case works.
    """

    def run_mock(qc, **kwargs):
        assert isinstance(qc, QuantumCircuit)
        assert 'calibration_set_id' in kwargs
        assert kwargs['calibration_set_id'] == '92d8dd9a-2678-467e-a20b-ef9c1a594d1f'
        assert 'something_else' in kwargs
        assert kwargs['something_else'] == [1, 2, 3]

    patch(backend.run, run_mock)
    execute(
        circuit, backend, shots=10, calibration_set_id='92d8dd9a-2678-467e-a20b-ef9c1a594d1f', something_else=[1, 2, 3]
    )


def test_run_single_circuit(backend, qubit_mapping, circuit):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    when(backend.client).submit_circuits(
        [circuit_ser], qubit_mapping=qubit_mapping, calibration_set_id=None, shots=shots
    ).thenReturn(some_id)
    job = backend.run(circuit, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit], shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_run_sets_circuit_metadata_to_the_job(backend):
    circuit_1 = QuantumCircuit(3)
    circuit_1.metadata = {'key1': 'value1', 'key2': 'value2'}
    circuit_2 = QuantumCircuit(3)
    circuit_2.metadata = {'key1': 'value2', 'key2': 'value1'}
    some_id = uuid.uuid4()
    backend.client.submit_circuits = lambda *args, **kwargs: some_id
    job = backend.run([circuit_1, circuit_2], shots=10)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)
    assert job.circuit_metadata == [circuit_1.metadata, circuit_2.metadata]


def test_run_with_custom_calibration_set_id(backend, qubit_mapping, circuit):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    some_id = uuid.uuid4()
    shots = 10
    calibration_set_id = '67e77465-d90e-4839-986e-9270f952b743'
    when(backend.client).submit_circuits(
        [circuit_ser], qubit_mapping=qubit_mapping, calibration_set_id=calibration_set_id, shots=shots
    ).thenReturn(some_id)

    backend.run([circuit], calibration_set_id=calibration_set_id, shots=shots)


def test_run_batch_of_circuits(backend, qubit_mapping, circuit):
    theta = Parameter('theta')
    theta_range = np.linspace(0, 2 * np.pi, 3)
    shots = 10
    some_id = uuid.uuid4()
    circuit.cz(0, 1)
    circuit.r(theta, 0, 0)
    circuit.cz(0, 1)
    circuits = [circuit.bind_parameters({theta: t}) for t in theta_range]
    circuits_serialized = [backend.serialize_circuit(circuit) for circuit in circuits]
    when(backend.client).submit_circuits(
        circuits_serialized, qubit_mapping=qubit_mapping, calibration_set_id=None, shots=shots
    ).thenReturn(some_id)

    job = backend.run(circuits, shots=shots)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)


def test_error_on_empty_circuit_list(backend):
    with pytest.raises(ValueError, match='Empty list of circuits submitted for execution.'):
        backend.run([], shots=42)


def test_close_client(backend):
    when(backend.client).close_auth_session().thenReturn(True)
    try:
        backend.close_client()
    except Exception as exc:  # pylint: disable=broad-except
        assert False, f'backend raised an exception {exc} on .close_client()'
