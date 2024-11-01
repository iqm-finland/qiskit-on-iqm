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
"""Qiskit backend provider for IQM backends.
"""
from __future__ import annotations

from copy import copy
from importlib.metadata import PackageNotFoundError, version
from functools import reduce
from typing import Collection, Optional, Union
from uuid import UUID
import warnings

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Clbit
from qiskit.providers import JobStatus, JobV1, Options

from iqm.iqm_client import (
    Circuit,
    CircuitCompilationOptions,
    CircuitValidationError,
    Instruction,
    IQMClient,
    RunRequest,
)
from iqm.iqm_client.util import to_json_dict
from iqm.qiskit_iqm.fake_backends import IQMFakeAdonis
from iqm.qiskit_iqm.iqm_backend import IQMBackendBase
from iqm.qiskit_iqm.iqm_job import IQMJob
from iqm.qiskit_iqm.qiskit_to_iqm import MeasurementKey

try:
    __version__ = version('qiskit-iqm')
except PackageNotFoundError:  # pragma: no cover
    __version__ = 'unknown'
finally:
    del version, PackageNotFoundError


class IQMBackend(IQMBackendBase):
    """Backend for executing quantum circuits on IQM quantum computers.

    Args:
        client: client instance for communicating with an IQM server
        calibration_set_id: ID of the calibration set the backend will use.
            ``None`` means the IQM server will be queried for the current default
            calibration set.
        kwargs: optional arguments to be passed to the parent Backend initializer
    """

    def __init__(self, client: IQMClient, *, calibration_set_id: Union[str, UUID, None] = None, **kwargs):
        if calibration_set_id is not None and not isinstance(calibration_set_id, UUID):
            calibration_set_id = UUID(calibration_set_id)
        self._use_default_calibration_set = calibration_set_id is None
        architecture = client.get_dynamic_quantum_architecture(calibration_set_id)
        super().__init__(architecture, **kwargs)
        self.client: IQMClient = client
        self._max_circuits: Optional[int] = None
        self.name = 'IQM Backend'
        self._calibration_set_id = architecture.calibration_set_id

    @classmethod
    def _default_options(cls) -> Options:
        return Options(
            shots=1024,
            circuit_compilation_options=CircuitCompilationOptions(),
            circuit_callback=None,
        )

    @property
    def max_circuits(self) -> Optional[int]:
        """Maximum number of circuits that should be run in a single batch.

        Currently there is no hard limit on the number of circuits that can be executed in a single batch/job.
        However, some libraries like Qiskit Experiments use this property to split multi-circuit computational
        tasks into multiple baches/jobs.

        The default value is ``None``, meaning there is no limit. You can set it to a specific integer
        value to force these libraries to run at most that many circuits in a single batch.
        """
        return self._max_circuits

    @max_circuits.setter
    def max_circuits(self, value: Optional[int]) -> None:
        self._max_circuits = value

    def run(
        self,
        run_input: Union[QuantumCircuit, list[QuantumCircuit]],
        *,
        timeout_seconds: Optional[float] = None,
        **options,
    ) -> IQMJob:
        """Run a quantum circuit or a list of quantum circuits on the IQM quantum computer represented by this backend.

        Args:
            run_input: The circuits to run.
            timeout_seconds: Maximum time to wait for the job to finish, in seconds. If ``None``, use
                the :class:`~iqm.iqm_client.iqm_client.IQMClient` default.
            options: Keyword arguments passed on to :meth:`create_run_request`, and documented there.

        Returns:
            Job object from which the results can be obtained once the execution has finished.
        """

        timeout_seconds = options.pop('timeout_seconds', None)
        run_request = self.create_run_request(run_input, **options)
        job_id = self.client.submit_run_request(run_request)
        job = IQMJob(self, str(job_id), shots=run_request.shots, timeout_seconds=timeout_seconds)
        job.circuit_metadata = [c.metadata for c in run_request.circuits]
        return job

    def create_run_request(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> RunRequest:
        """Creates a run request without submitting it for execution.

        This can be used to check what would be submitted for execution by an equivalent call to :meth:`run`.

        Args:
            run_input: Same as in :meth:`run`.

        Keyword Args:
            shots (int): Number of repetitions of each circuit, for sampling. Default is 1024.
            circuit_compilation_options (iqm.iqm_client.models.CircuitCompilationOptions):
                Compilation options for the circuits, passed on to :mod:`iqm-client`.
            circuit_callback (collections.abc.Callable[[list[QuantumCircuit]], Any]):
                Callback function that, if provided, will be called for the circuits before sending
                them to the device.  This may be useful in situations when you do not have explicit
                control over transpilation, but need some information on how it was done. This can
                happen, for example, when you use pre-implemented algorithms and experiments in
                Qiskit, where the implementation of the said algorithm or experiment takes care of
                delivering correctly transpiled circuits to the backend. This callback method gives
                you a chance to look into those transpiled circuits, and extract any info you need.
                As a side effect, you can also use this callback to modify the transpiled circuits
                in-place, just before execution; however, we do not recommend to use it for this
                purpose.

        Returns:
            created run request object

        """
        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError('Empty list of circuits submitted for execution.')

        unknown_options = set(options.keys()) - set(self.options.keys())
        # Catch old iqm-client options
        if 'max_circuit_duration_over_t2' in unknown_options and 'circuit_compilation_options' not in options:
            self.options['circuit_compilation_options'].max_circuit_duration_over_t2 = options.pop(
                'max_circuit_duration_over_t2'
            )
            unknown_options.remove('max_circuit_duration_over_t2')
        if 'heralding_mode' in unknown_options and 'circuit_compilation_options' not in options:
            self.options['circuit_compilation_options'].heralding_mode = options.pop('heralding_mode')
            unknown_options.remove('heralding_mode')

        if unknown_options:
            warnings.warn(f'Unknown backend option(s): {unknown_options}')

        # merge given options with default options and get resulting values
        merged_options = copy(self.options)
        merged_options.update_options(**dict(options))
        shots = merged_options['shots']

        circuit_callback = merged_options['circuit_callback']
        if circuit_callback:
            circuit_callback(circuits)

        circuits_serialized: list[Circuit] = [self.serialize_circuit(circuit) for circuit in circuits]
        used_physical_qubit_indices: set[int] = reduce(
            lambda qubits, circuit: qubits.union(set(int(q) for q in circuit.all_qubits())), circuits_serialized, set()
        )
        qubit_mapping = {str(idx): qb for idx, qb in self._idx_to_qb.items() if idx in used_physical_qubit_indices}

        if self._use_default_calibration_set:
            default_calset_id = self.client.get_dynamic_quantum_architecture(None).calibration_set_id
            if self._calibration_set_id != default_calset_id:
                warnings.warn(
                    f'Server default calibration set has changed from {self._calibration_set_id} '
                    f'to {default_calset_id}. Create a new IQMBackend if you wish to transpile the '
                    'circuits using the new calibration set.'
                )
        try:
            run_request = self.client.create_run_request(
                circuits_serialized,
                qubit_mapping=qubit_mapping,
                calibration_set_id=self._calibration_set_id,
                shots=shots,
                options=merged_options['circuit_compilation_options'],
            )
        except CircuitValidationError as e:
            raise CircuitValidationError(
                f'{e}\nMake sure the circuits have been transpiled using the same backend that you used to submit '
                f'the circuits.'
            ) from e

        return run_request

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id."""
        return IQMJob(self, job_id)

    def close_client(self) -> None:
        """Close IQMClient's session with the authentication server."""
        self.client.close_auth_session()

    def serialize_circuit(self, circuit: QuantumCircuit) -> Circuit:
        """Serialize a quantum circuit into the IQM data transfer format.

        Serializing is not strictly bound to the native gateset, i.e. some gates that are not explicitly mentioned in
        the native gateset of the backend can still be serialized. For example, the native single qubit gate for IQM
        backend is the 'r' gate, however 'x', 'rx', 'y' and 'ry' gates can also be serialized since they are just
        particular cases of the 'r' gate. If the circuit was transpiled against a backend using Qiskit's transpiler
        machinery, these gates are not supposed to be present. However, when constructing circuits manually and
        submitting directly to the backend, it is sometimes more explicit and understandable to use these concrete
        gates rather than 'r'. Serializing them explicitly makes it possible for the backend to accept such circuits.

        Qiskit uses one measurement instruction per qubit (i.e. there is no measurement grouping concept). While
        serializing we do not group any measurements together but rather associate a unique measurement key with each
        measurement instruction, so that the results can later be reconstructed correctly (see :class:`.MeasurementKey`
        documentation for more details).

        Args:
            circuit: quantum circuit to serialize

        Returns:
            data transfer object representing the circuit

        Raises:
            ValueError: circuit contains an unsupported instruction or is not transpiled in general
        """
        instructions = _serialize_instructions(circuit, self._idx_to_qb)

        try:
            metadata = to_json_dict(circuit.metadata)
        except ValueError:
            warnings.warn(
                f'Metadata of circuit {circuit.name} was dropped because it could not be serialised to JSON.',
            )
            metadata = None

        return Circuit(name=circuit.name, instructions=instructions, metadata=metadata)


def _serialize_instructions(
    circuit: QuantumCircuit, qubit_index_to_name: dict[int, str], allowed_nonnative_gates: Collection[str] = ()
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
        qubit_names = [str(circuit.find_bit(qubit).index) for qubit in circuit_instruction.qubits]
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
            # implemented using a measure instruction to measure the qubits, and
            # one cc_prx per qubit to conditionally flip it to |0>
            feedback_key = '_reset'
            instructions.append(
                Instruction(
                    name='measure',
                    qubits=qubit_names,
                    args={
                        # HACK to get something unique, remove when key can be omitted
                        'key': f'_reset_{len(instructions)}',
                        'feedback_key': feedback_key,
                    },
                )
            )
            for q in qubit_names:
                physical_qubit_name = qubit_index_to_name[int(q)]
                instructions.append(
                    Instruction(
                        name='cc_prx',
                        qubits=[q],
                        args={
                            'angle_t': 0.5,
                            'phase_t': 0.0,
                            'feedback_key': feedback_key,
                            'feedback_qubit': physical_qubit_name,
                        },
                    )
                )
            continue
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
        condition = instruction.condition
        if condition is not None:
            if native_inst.name != 'prx':
                raise ValueError(
                    'This backend only supports conditionals on r, x, y, rx and ry gates,' f' not on {instruction.name}'
                )
            native_inst.name = 'cc_prx'
            creg, value = condition
            if len(creg) != 1:
                raise ValueError(f'{instruction} is conditioned on multiple bits, this is not supported.')
            if value != 1:
                raise ValueError(f'{instruction} is conditioned on integer value {value}, only value 1 is supported.')
            # Set up feedback routing.
            # The latest "measure" instruction to write to that classical bit is modified, it is
            # given an explicit feedback_key equal to its measurement key.
            # The same feedback_key is given to the controlled instruction, along with the feedback qubit.
            measure_inst = clbit_to_measure[creg[0]]
            feedback_key = measure_inst.args['key']
            measure_inst.args['feedback_key'] = feedback_key  # this measure is used to provide feedback
            # TODO we should use physical qubit names in native circuits, not integer strings
            physical_qubit_name = qubit_index_to_name[int(measure_inst.qubits[0])]  # single-qubit measurement
            native_inst.args['feedback_key'] = feedback_key
            native_inst.args['feedback_qubit'] = physical_qubit_name

        instructions.append(native_inst)
    return instructions


class IQMFacadeBackend(IQMBackend):
    """Facade backend for mimicking the execution of quantum circuits on IQM quantum computers. Allows to submit a
     circuit to the IQM server, and if the execution was successful, performs a simulation with a respective IQM noise
     model locally, then returns the simulated results.

    Args:
        client: client instance for communicating with an IQM server
        **kwargs: optional arguments to be passed to the parent Backend initializer
    """

    def __init__(self, client: IQMClient, **kwargs):
        self.fake_adonis = IQMFakeAdonis()
        target_architecture = client.get_dynamic_quantum_architecture(kwargs.get('calibration_set_id', None))

        if not self.fake_adonis.validate_compatible_architecture(target_architecture):
            raise ValueError('Quantum architecture of the remote quantum computer does not match Adonis.')

        super().__init__(client, **kwargs)
        self.name = 'facade_adonis'

    def _validate_no_empty_cregs(self, circuit: QuantumCircuit) -> bool:
        """Returns True if given circuit has no empty (unused) classical registers, False otherwise."""
        cregs_utilization = dict.fromkeys(circuit.cregs, 0)
        used_cregs = [circuit.find_bit(i.clbits[0]).registers[0][0] for i in circuit.data if len(i.clbits) > 0]
        for creg in used_cregs:
            cregs_utilization[creg] += 1

        if 0 in cregs_utilization.values():
            return False
        return True

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> JobV1:
        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input
        circuits_validated_cregs: list[bool] = [self._validate_no_empty_cregs(circuit) for circuit in circuits]
        if not all(circuits_validated_cregs):
            raise ValueError(
                'One or more circuits contain unused classical registers. This is not allowed for Facade simulation, '
                'see user guide.'
            )

        iqm_backend_job = super().run(run_input, **options)
        iqm_backend_job.result()  # get and discard results
        if iqm_backend_job.status() == JobStatus.ERROR:
            raise RuntimeError('Remote execution did not succeed.')
        return self.fake_adonis.run(run_input, **options)


class IQMProvider:
    """Provider for IQM backends.

    Args:
        url: URL of the IQM Cortex server

    Keyword Args:
        auth_server_url: URL of the user authentication server, if required by the IQM Cortex server.
            Can also be set in the ``IQM_AUTH_SERVER`` environment variable.
        username: Username, if required by the IQM Cortex server.
            Can also be set in the ``IQM_AUTH_USERNAME`` environment variable.
        password: Password, if required by the IQM Cortex server.
            Can also be set in the ``IQM_AUTH_PASSWORD`` environment variable.
    """

    def __init__(self, url: str, **user_auth_args):  # contains keyword args auth_server_url, username, password
        self.url = url
        self.user_auth_args = user_auth_args

    def get_backend(
        self, name: Optional[str] = None, calibration_set_id: Optional[UUID] = None
    ) -> Union[IQMBackend, IQMFacadeBackend]:
        """An IQMBackend instance associated with this provider.

        Args:
            name: optional name of a custom facade backend
            calibration_set_id: ID of the calibration set used to create the transpilation target of the backend.
                If None, the server default calibration set will be used.
        """
        client = IQMClient(self.url, client_signature=f'qiskit-iqm {__version__}', **self.user_auth_args)
        if name == 'facade_adonis':
            return IQMFacadeBackend(client)
        return IQMBackend(client, calibration_set_id=calibration_set_id)
