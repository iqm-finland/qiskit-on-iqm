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
from collections.abc import Sequence
from importlib.metadata import version
import re
import uuid

from mockito import ANY, expect, matchers, mock, unstub, verifyNoUnwantedInteractions, when
import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import RGate, RXGate, RYGate, XGate, YGate
import requests

from iqm.iqm_client import (
    CircuitCompilationOptions,
    CircuitExecutionError,
    HeraldingMode,
    IQMClient,
    QuantumArchitecture,
    RunRequest,
    RunResult,
    RunStatus,
)
from iqm.qiskit_iqm.iqm_provider import IQMBackend, IQMFacadeBackend, IQMJob, IQMProvider
from tests.utils import get_mock_ok_response


@pytest.fixture
def backend(linear_architecture_3q):
    client = mock(IQMClient)
    when(client).get_quantum_architecture().thenReturn(linear_architecture_3q)
    client._base_url = 'http://some_url'
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
def create_run_request_default_kwargs() -> dict:
    return {'qubit_mapping': None, 'calibration_set_id': None, 'shots': 1024, 'options': ANY}


@pytest.fixture
def job_id():
    return uuid.uuid4()


@pytest.fixture
def run_request():
    run_request = mock(RunRequest)
    run_request.circuits = []
    run_request.shots = 1
    return run_request


def test_default_options(backend):
    assert backend.options.shots == 1024
    assert backend.options.calibration_set_id is None
    for k, v in backend.options.circuit_compilation_options.__dict__.items():
        assert v == CircuitCompilationOptions().__dict__[k]
    assert backend.options.circuit_compilation_options
    assert backend.options.circuit_callback is None


def test_backend_name(backend):
    assert re.match(r'IQM(.*)Backend', backend.name)


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


def test_serialize_circuit_raises_error_for_non_transpiled_circuit(circuit, linear_architecture_3q):
    client = IQMClient(url='http://some_url')
    client._token_manager = None  # Do not use authentication
    when(client).get_quantum_architecture().thenReturn(linear_architecture_3q)
    backend = IQMBackend(client)
    circuit = QuantumCircuit(3)
    circuit.cz(0, 2)
    with pytest.raises(
        CircuitExecutionError, match=re.escape("'0', '2') = ('QB1', 'QB3') not allowed as locus for cz")
    ):
        backend.run(circuit)


def test_serialize_circuit_raises_error_for_unsupported_instruction(backend, circuit):
    circuit.sx(0)
    with pytest.raises(ValueError, match=f"Instruction 'sx' in the circuit '{circuit.name}' is not natively supported"):
        backend.serialize_circuit(circuit)


def test_serialize_circuit_does_not_raise_for_x_rx_y_ry(backend, circuit):
    circuit.x(0)
    circuit.rx(0.123, 0)
    circuit.y(0)
    circuit.ry(0.321, 0)
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
    assert instr.name == 'prx'
    assert instr.qubits == ('0',)
    # Serialized angles should be in full turns
    assert instr.args['angle_t'] == expected_angle
    assert instr.args['phase_t'] == expected_phase


@pytest.mark.parametrize(
    'gate, expected_angle, expected_phase',
    [
        (XGate(), 1 / 2, 0),
        (RXGate(theta=np.pi / 2), 1 / 4, 0),
        (RXGate(theta=2 * np.pi / 3), 1 / 3, 0),
        (YGate(), 1 / 2, 1 / 4),
        (RYGate(theta=np.pi / 2), 1 / 4, 1 / 4),
        (RYGate(theta=2 * np.pi / 3), 1 / 3, 1 / 4),
    ],
)
def test_serialize_circuit_maps_x_rx_y_ry_gates(backend, circuit, gate, expected_angle, expected_phase):
    circuit.append(gate, [0])
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 1
    instr = circuit_ser.instructions[0]
    assert instr.name == 'prx'
    assert instr.qubits == ('0',)
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
        assert instruction.name == 'measure'
        assert instruction.qubits == (f'{i}',)
        assert instruction.args == {'key': f'c_3_0_{i}'}


def test_serialize_circuit_batch_measurement(circuit, backend):
    circuit.measure([0, 1, 2], [0, 1, 2])
    circuit_ser = backend.serialize_circuit(circuit)
    assert len(circuit_ser.instructions) == 3
    for i, instruction in enumerate(circuit_ser.instructions):
        assert instruction.name == 'measure'
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
    assert circuit_ser.instructions[0].name == 'prx'


def test_transpile(backend, circuit):
    circuit.h(0)
    circuit.id(1)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 0)

    circuit_transpiled = transpile(circuit, backend=backend)
    cmap = backend.coupling_map.get_edges()
    for instr in circuit_transpiled.data:
        instruction = instr.operation
        qubits = instr.qubits
        assert instruction.name in ('r', 'cz')
        if instruction.name == 'cz':
            idx1 = circuit_transpiled.find_bit(qubits[0]).index
            idx2 = circuit_transpiled.find_bit(qubits[1]).index
            assert ((idx1, idx2) in cmap) or ((idx2, idx1) in cmap)


def test_run_non_native_circuit(backend, circuit, job_id, run_request):
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 2)

    when(backend.client).create_run_request(...).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    transpiled_circuit = transpile(circuit, backend, optimization_level=0)
    job = backend.run(transpiled_circuit)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)


def test_run_single_circuit(backend, circuit, create_run_request_default_kwargs, job_id, run_request):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = create_run_request_default_kwargs | {'qubit_mapping': {'0': 'QB1'}}
    when(backend.client).create_run_request([circuit_ser], **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    job = backend.run(circuit)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit])
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)


def test_run_sets_circuit_metadata_to_the_job(backend, run_request, job_id):
    circuit_1 = QuantumCircuit(3)
    circuit_1.cz(0, 1)
    circuit_1.metadata = {'key1': 'value1', 'key2': 'value2'}
    circuit_2 = QuantumCircuit(3)
    circuit_2.cz(0, 1)
    circuit_2.metadata = {'key1': 'value2', 'key2': 'value1'}
    run_request.circuits = [backend.serialize_circuit(c) for c in [circuit_1, circuit_2]]
    when(backend.client).create_run_request(...).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    job = backend.run([circuit_1, circuit_2], shots=10)
    assert isinstance(job, IQMJob)
    assert job.job_id() == str(job_id)
    assert job.circuit_metadata == [circuit_1.metadata, circuit_2.metadata]


@pytest.mark.parametrize('shots', [13, 978, 1137])
def test_run_with_custom_number_of_shots(
    backend, circuit, create_run_request_default_kwargs, job_id, shots, run_request
):
    # pylint: disable=too-many-arguments
    circuit.measure(0, 0)
    kwargs = create_run_request_default_kwargs | {'shots': shots, 'qubit_mapping': {'0': 'QB1'}}
    when(backend.client).create_run_request(ANY, **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    backend.run(circuit, shots=shots)


@pytest.mark.parametrize(
    'calibration_set_id', ['67e77465-d90e-4839-986e-9270f952b743', uuid.UUID('67e77465-d90e-4839-986e-9270f952b743')]
)
def test_run_with_custom_calibration_set_id(
    backend, circuit, create_run_request_default_kwargs, job_id, calibration_set_id, run_request
):
    # pylint: disable=too-many-arguments
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = create_run_request_default_kwargs | {
        'calibration_set_id': uuid.UUID('67e77465-d90e-4839-986e-9270f952b743'),
        'qubit_mapping': {'0': 'QB1'},
    }
    when(backend.client).create_run_request([circuit_ser], **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)

    backend.run([circuit], calibration_set_id=calibration_set_id)


def test_run_with_duration_check_disabled(backend, circuit, create_run_request_default_kwargs, job_id, run_request):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    options = CircuitCompilationOptions(max_circuit_duration_over_t2=0.0)
    kwargs = create_run_request_default_kwargs | {'qubit_mapping': {'0': 'QB1'}, 'options': options}
    when(backend.client).create_run_request([circuit_ser], **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)

    backend.run([circuit], circuit_compilation_options=options)


def test_run_uses_heralding_mode_none_by_default(
    backend, circuit, create_run_request_default_kwargs, job_id, run_request
):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    kwargs = create_run_request_default_kwargs | {
        'options': backend.options.circuit_compilation_options,
        'qubit_mapping': {'0': 'QB1'},
    }
    when(backend.client).create_run_request([circuit_ser], **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    backend.run([circuit])


def test_run_with_heralding_mode_zeros(backend, circuit, create_run_request_default_kwargs, job_id, run_request):
    circuit.measure(0, 0)
    circuit_ser = backend.serialize_circuit(circuit)
    options = CircuitCompilationOptions(heralding_mode=HeraldingMode.ZEROS)
    kwargs = create_run_request_default_kwargs | {
        'options': options,
        'qubit_mapping': {'0': 'QB1'},
    }
    when(backend.client).create_run_request([circuit_ser], **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    backend.run([circuit], circuit_compilation_options=options)


# mypy: disable-error-code="attr-defined"
def test_run_with_circuit_callback(backend, job_id, create_run_request_default_kwargs, run_request):
    qc1 = QuantumCircuit(3)
    qc1.measure_all()
    qc2 = QuantumCircuit(3)
    qc2.r(np.pi, 0.3, 0)
    qc2.measure_all()

    def sample_callback(circuits) -> None:
        assert isinstance(circuits, Sequence)
        assert all(isinstance(c, QuantumCircuit) for c in circuits)
        assert len(circuits) == 2
        assert circuits[0].name == qc1.name
        assert circuits[1].name == qc2.name
        sample_callback.called = True

    sample_callback.called = False

    kwargs = create_run_request_default_kwargs | {'qubit_mapping': {'0': 'QB1', '1': 'QB2', '2': 'QB3'}}
    when(backend.client).create_run_request(ANY, **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    backend.run([qc1, qc2], circuit_callback=sample_callback)
    assert sample_callback.called is True


def test_run_with_unknown_option(backend, circuit, job_id, run_request):
    circuit.measure_all()
    when(backend.client).create_run_request(...).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)
    with pytest.warns(Warning, match=r'Unknown backend option\(s\)'):
        backend.run(circuit, to_option_or_not_to_option=17)


def test_run_batch_of_circuits(backend, circuit, create_run_request_default_kwargs, job_id, run_request):
    theta = Parameter('theta')
    theta_range = np.linspace(0, 2 * np.pi, 3)
    circuit.cz(0, 1)
    circuit.r(theta, 0, 0)
    circuit.cz(0, 1)
    circuits = [circuit.assign_parameters({theta: t}) for t in theta_range]
    circuits_serialized = [backend.serialize_circuit(circuit) for circuit in circuits]
    kwargs = create_run_request_default_kwargs | {'qubit_mapping': {'0': 'QB1', '1': 'QB2'}}
    when(backend.client).create_run_request(circuits_serialized, **kwargs).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(job_id)

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


def test_client_signature(adonis_architecture):
    url = 'http://some_url'
    provider = IQMProvider(url)
    when(requests).get('http://some_url/quantum-architecture', headers=matchers.ANY, timeout=matchers.ANY).thenReturn(
        get_mock_ok_response(QuantumArchitecture(quantum_architecture=adonis_architecture).model_dump())
    )
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


def test_facade_backend_raises_error_on_remote_execution_fail(adonis_architecture, circuit_2, run_request):
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
                        'instructions': [{'name': 'measure', 'qubits': ['0'], 'args': {'key': 'm1'}}],
                    }
                ],
            }
        },
    }
    result_status = {'status': 'failed'}

    when(IQMClient).get_quantum_architecture().thenReturn(adonis_architecture)
    when(IQMClient).create_run_request(...).thenReturn(run_request)
    when(IQMClient).submit_run_request(...).thenReturn(uuid.uuid4())
    when(IQMClient).get_run(ANY(uuid.UUID)).thenReturn(RunResult.from_dict(result))
    when(IQMClient).get_run_status(ANY(uuid.UUID)).thenReturn(RunStatus.from_dict(result_status))

    provider = IQMProvider(url)
    backend = provider.get_backend('facade_adonis')

    with pytest.raises(RuntimeError, match='Remote execution did not succeed'):
        backend.run(circuit_2)


def test_create_run_request(backend, circuit, create_run_request_default_kwargs, run_request):
    options = {'optimization_level': 0}

    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 2)

    circuit_transpiled = transpile(circuit, backend, **options)
    circuit_serialized = backend.serialize_circuit(circuit_transpiled)
    kwargs = create_run_request_default_kwargs | {'qubit_mapping': {'0': 'QB1', '1': 'QB2', '2': 'QB3'}}

    # verifies that backend.create_run_request() and backend.run() call client.create_run_request() with same arguments
    expect(backend.client, times=2).create_run_request(
        [circuit_serialized],
        **kwargs,
    ).thenReturn(run_request)
    when(backend.client).submit_run_request(run_request).thenReturn(uuid.uuid4())

    assert backend.create_run_request(circuit_transpiled) == run_request
    backend.run(circuit_transpiled)

    verifyNoUnwantedInteractions()
    unstub()
