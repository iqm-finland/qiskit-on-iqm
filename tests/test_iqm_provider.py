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

"""Testing IQM provider.
"""
from importlib.metadata import version
import uuid

from mockito import ANY, mock, patch, when
import numpy as np
import pytest
from qiskit import QuantumCircuit, execute
from qiskit.circuit import Parameter
from qiskit.circuit.library import RGate
from qiskit.compiler import transpile

from iqm.iqm_client import HeraldingMode, IQMClient, RunResult, RunStatus
from iqm.qiskit_iqm import IQMBackend, IQMJob, IQMProvider
from iqm.qiskit_iqm.iqm_provider import IQMFacadeBackend


@pytest.fixture
def backend(linear_architecture_3q):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(linear_architecture_3q)
    return IQMBackend(client)


@pytest.fixture
def circuit():
    return QuantumCircuit(3, 3)


@pytest.fixture
def circuit_2() -> QuantumCircuit:
    circuit = QuantumCircuit(5)
    circuit.cz(0, 1)
    return circuit


@pytest.fixture
def submit_circuits_default_kwargs() -> dict:
    return {
        'qubit_mapping': None,
        'calibration_set_id': None,
        'shots': 1024,
        'circuit_duration_check': True,
        'heralding_mode': HeraldingMode.NONE,
    }


@pytest.fixture
def job_id():
    return uuid.uuid4()


def test_default_options(backend):
    assert backend.options.shots == 1024
    assert backend.options.calibration_set_id is None


def test_retrieve_job(backend):
    job = backend.retrieve_job('a job id')
    assert job.backend() == backend
    assert job.job_id() == 'a job id'


def test_default_max_circuits(backend):
    assert backend.max_circuits is None


def test_set_max_circuits(backend):
    assert backend.max_circuits is None

    backend.max_circuits = 17
    assert backend.max_circuits == 17

    backend.max_circuits = 168
    assert backend.max_circuits == 168


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


def test_serialize_circuit_raises_error_for_unsupported_metadata(backend, circuit):
    circuit.append(RGate(theta=np.pi, phi=0), [0])
    circuit.metadata = {'some-key': complex(1.0, 2.0)}
    with pytest.warns(UserWarning):
        serialized_circuit = backend.serialize_circuit(circuit)
    assert serialized_circuit.metadata is None


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


def test_serialize_circuit_id(circuit, backend):
    circuit.r(theta=np.pi, phi=0, qubit=0)
    circuit.id(0)
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    assert circuit_ser.instructions[0].name == 'phased_rx'


def test_transpile(backend, circuit):
    circuit.h(0)
    circuit.id(1)
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


def test_run_single_circuit(backend, circuit, submit_circuits_default_kwargs, job_id):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = submit_circuits_default_kwargs | {'qubit_mapping': {'0': 'QB1'}}
    when(backend.client).submit_circuits([circuit_ser], **kwargs).thenReturn(job_id)
    job = backend.run(circuit)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit])
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)


def test_run_sets_circuit_metadata_to_the_job(backend):
    circuit_1 = QuantumCircuit(3)
    circuit_1.cz(0, 1)
    circuit_1.metadata = {'key1': 'value1', 'key2': 'value2'}
    circuit_2 = QuantumCircuit(3)
    circuit_2.cz(0, 1)
    circuit_2.metadata = {'key1': 'value2', 'key2': 'value1'}
    some_id = uuid.uuid4()
    backend.client.submit_circuits = lambda *args, **kwargs: some_id
    job = backend.run([circuit_1, circuit_2], shots=10)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(some_id)
    assert job.circuit_metadata == [circuit_1.metadata, circuit_2.metadata]


@pytest.mark.parametrize(
    'calibration_set_id', ['67e77465-d90e-4839-986e-9270f952b743', uuid.UUID('67e77465-d90e-4839-986e-9270f952b743')]
)
def test_run_with_custom_calibration_set_id(
    backend, circuit, submit_circuits_default_kwargs, job_id, calibration_set_id
):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = submit_circuits_default_kwargs | {
        'calibration_set_id': uuid.UUID('67e77465-d90e-4839-986e-9270f952b743'),
        'qubit_mapping': {'0': 'QB1'},
    }
    when(backend.client).submit_circuits([circuit_ser], **kwargs).thenReturn(job_id)

    backend.run([circuit], calibration_set_id=calibration_set_id)


def test_run_with_duration_check_disabled(backend, circuit, submit_circuits_default_kwargs, job_id):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = submit_circuits_default_kwargs | {'qubit_mapping': {'0': 'QB1'}, 'circuit_duration_check': False}
    when(backend.client).submit_circuits([circuit_ser], **kwargs).thenReturn(job_id)

    backend.run([circuit], circuit_duration_check=False)


def test_run_uses_heralding_mode_none_by_default(backend, circuit, submit_circuits_default_kwargs, job_id):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = submit_circuits_default_kwargs | {'heralding_mode': HeraldingMode.NONE, 'qubit_mapping': {'0': 'QB1'}}
    when(backend.client).submit_circuits([circuit_ser], **kwargs).thenReturn(job_id)
    backend.run([circuit])


def test_run_with_heralding_mode_zeros(backend, circuit, submit_circuits_default_kwargs, job_id):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = submit_circuits_default_kwargs | {'heralding_mode': HeraldingMode.ZEROS, 'qubit_mapping': {'0': 'QB1'}}
    when(backend.client).submit_circuits([circuit_ser], **kwargs).thenReturn(job_id)
    backend.run([circuit], heralding_mode='zeros')


def test_run_batch_of_circuits(backend, circuit, submit_circuits_default_kwargs, job_id):
    theta = Parameter('theta')
    theta_range = np.linspace(0, 2 * np.pi, 3)
    circuit.cz(0, 1)
    circuit.r(theta, 0, 0)
    circuit.cz(0, 1)
    circuits = [circuit.bind_parameters({theta: t}) for t in theta_range]
    circuits_serialized = [backend.serialize_circuit(circuit) for circuit in circuits]
    kwargs = submit_circuits_default_kwargs | {'qubit_mapping': {'0': 'QB1', '1': 'QB2'}}
    when(backend.client).submit_circuits(circuits_serialized, **kwargs).thenReturn(job_id)

    job = backend.run(circuits)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)


def test_error_on_empty_circuit_list(backend):
    with pytest.raises(ValueError, match='Empty list of circuits submitted for execution.'):
        backend.run([], shots=42)


def test_close_client(backend):
    when(backend.client).close_auth_session().thenReturn(True)
    try:
        backend.close_client()
    except Exception as exc:  # pylint: disable=broad-except
        assert False, f'backend raised an exception {exc} on .close_client()'


def test_get_backend(linear_architecture_3q):
    url = 'http://some_url'
    when(IQMClient).get_quantum_architecture().thenReturn(linear_architecture_3q)

    provider = IQMProvider(url)
    backend = provider.get_backend()

    assert isinstance(backend, IQMBackend)
    assert backend.client._base_url == url
    assert backend.num_qubits == 3
    assert set(backend.coupling_map.get_edges()) == {(0, 1), (1, 0), (1, 2), (2, 1)}


def test_client_signature():
    url = 'http://some_url'
    provider = IQMProvider(url)
    backend = provider.get_backend()
    assert f'qiskit-iqm {version("qiskit-iqm")}' in backend.client._signature


def test_get_facade_backend(adonis_architecture, adonis_coupling_map):
    url = 'http://some_url'
    when(IQMClient).get_quantum_architecture().thenReturn(adonis_architecture)

    provider = IQMProvider(url)
    backend = provider.get_backend('facade_adonis')

    assert isinstance(backend, IQMFacadeBackend)
    assert backend.client._base_url == url
    assert backend.num_qubits == 5
    assert set(backend.coupling_map.get_edges()) == adonis_coupling_map


def test_get_facade_backend_raises_error_non_matching_architecture(linear_architecture_3q):
    url = 'http://some_url'

    when(IQMClient).get_quantum_architecture().thenReturn(linear_architecture_3q)

    provider = IQMProvider(url)
    with pytest.raises(ValueError, match='Quantum architecture of the remote quantum computer does not match Adonis.'):
        provider.get_backend('facade_adonis')


def test_facade_backend_raises_error_on_remote_execution_fail(adonis_architecture, circuit_2):
    url = 'http://some_url'
    result = {
        'status': 'failed',
        'measurements': [],
        'metadata': {
            'request': {
                'shots': 1024,
                'circuits': [
                    {
                        'name': 'circuit_2',
                        'instructions': [{'name': 'measurement', 'qubits': ['0'], 'args': {'key': 'm1'}}],
                    }
                ],
            }
        },
    }
    result_status = {'status': 'failed'}

    when(IQMClient).get_quantum_architecture().thenReturn(adonis_architecture)
    when(IQMClient).submit_circuits(...).thenReturn(uuid.uuid4())
    when(IQMClient).get_run(ANY(uuid.UUID)).thenReturn(RunResult.from_dict(result))
    when(IQMClient).get_run_status(ANY(uuid.UUID)).thenReturn(RunStatus.from_dict(result_status))

    provider = IQMProvider(url)
    backend = provider.get_backend('facade_adonis')

    with pytest.raises(RuntimeError, match='Remote execution did not succeed'):
        backend.run(circuit_2)
