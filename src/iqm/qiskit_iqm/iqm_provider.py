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

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Optional, Union
from uuid import UUID
import warnings

from qiskit import QuantumCircuit
from qiskit.providers import JobStatus, JobV1, Options

from iqm.iqm_client import Circuit, CircuitCompilationOptions, CircuitValidationError, IQMClient, RunRequest
from iqm.iqm_client.util import to_json_dict
from iqm.qiskit_iqm.fake_backends import IQMFakeAdonis
from iqm.qiskit_iqm.iqm_backend import IQMBackendBase
from iqm.qiskit_iqm.iqm_job import IQMJob
from iqm.qiskit_iqm.qiskit_to_iqm import serialize_instructions

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
        """Qiskit method for defining the default options for running the backend. We don't use them since they would
        not be documented here. Instead, we use the keyword arguments of the run method to pass options.
        """
        return Options()

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

    # pylint: disable=too-many-arguments
    def create_run_request(
        self,
        run_input: Union[QuantumCircuit, list[QuantumCircuit]],
        shots: int = 1024,
        circuit_compilation_options: Optional[CircuitCompilationOptions] = None,
        circuit_callback: Optional[Callable[[list[QuantumCircuit]], Any]] = None,
        qubit_mapping: Optional[dict[int, str]] = None,
        **unknown_options,
    ) -> RunRequest:
        """Creates a run request without submitting it for execution.

        This can be used to check what would be submitted for execution by an equivalent call to :meth:`run`.

        Args:
            run_input: Same as in :meth:`run`.

        Args:
            shots: Number of repetitions of each circuit, for sampling.
            circuit_compilation_options:
                Compilation options for the circuits, passed on to :class:`~iqm.iqm_client.iqm_client.IQMClient`.
                If ``None``, the defaults of the :class:`~iqm.iqm_client.models.CircuitCompilationOptions`
                class are used.
            circuit_callback:
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
            qubit_mapping: Mapping from qubit indices in the circuit to qubit names on the device. If ``None``,
                :attr:`.IQMBackendBase.index_to_qubit_name` will be used.

        Returns:
            The created run request object

        """
        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError('Empty list of circuits submitted for execution.')

        # Catch old iqm-client options
        if 'max_circuit_duration_over_t2' in unknown_options or 'heralding_mode' in unknown_options:
            warnings.warn(
                DeprecationWarning(
                    'max_circuit_duration_over_t2 and heralding_mode are deprecated, please use '
                    + 'circuit_compilation_options instead.'
                )
            )
        if circuit_compilation_options is None:
            cc_options_kwargs = {}
            if 'max_circuit_duration_over_t2' in unknown_options:
                cc_options_kwargs['max_circuit_duration_over_t2'] = unknown_options.pop('max_circuit_duration_over_t2')
            if 'heralding_mode' in unknown_options:
                cc_options_kwargs['heralding_mode'] = unknown_options.pop('heralding_mode')
            circuit_compilation_options = CircuitCompilationOptions(**cc_options_kwargs)

        if unknown_options:
            warnings.warn(f'Unknown backend option(s): {unknown_options}')

        if circuit_callback:
            circuit_callback(circuits)

        circuits_serialized: list[Circuit] = [self.serialize_circuit(circuit, qubit_mapping) for circuit in circuits]

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
                calibration_set_id=self._calibration_set_id,
                shots=shots,
                options=circuit_compilation_options,
            )
        except CircuitValidationError as e:
            raise CircuitValidationError(
                f'{e}\nMake sure the circuits have been transpiled using the same backend that you used to submit '
                f'the circuits.'
            ) from e

        return run_request

    def retrieve_job(self, job_id: str) -> IQMJob:
        """Create and return an IQMJob instance associated with this backend with given job id.

        Args:
            job_id: ID of the job to retrieve.

        Returns:
            corresponding job
        """
        return IQMJob(self, job_id)

    def close_client(self) -> None:
        """Close IQMClient's session with the authentication server."""
        self.client.close_auth_session()

    def serialize_circuit(self, circuit: QuantumCircuit, qubit_mapping: Optional[dict[int, str]] = None) -> Circuit:
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
            qubit_mapping: Mapping from qubit indices in the circuit to qubit names on the device. If not provided,
                :attr:`.IQMBackendBase.index_to_qubit_name` will be used.

        Returns:
            data transfer object representing the circuit

        Raises:
            ValueError: circuit contains an unsupported instruction or is not transpiled in general
        """
        if qubit_mapping is None:
            qubit_mapping = self._idx_to_qb
        instructions = serialize_instructions(circuit, qubit_index_to_name=qubit_mapping)

        try:
            metadata = to_json_dict(circuit.metadata)
        except ValueError:
            warnings.warn(
                f'Metadata of circuit {circuit.name} was dropped because it could not be serialised to JSON.',
            )
            metadata = None

        return Circuit(name=circuit.name, instructions=instructions, metadata=metadata)


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

    IQMProvider connects to a quantum computer through an IQM server.
    If the server requires user authentication, you can provide it either using environment
    variables, or as keyword arguments to IQMProvider. The user authentication kwargs are passed
    through to :class:`~iqm.iqm_client.iqm_client.IQMClient` as is, and are documented there.

    Args:
        url: URL of the IQM server (e.g. https://cocos.resonance.meetiqm.com/garnet)
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

        if name and name.startswith('facade_'):
            if name == 'facade_adonis':
                return IQMFacadeBackend(client)

            warnings.warn(f'Unknown facade backend: {name}. A regular backend associated with {self.url} will be used.')

        return IQMBackend(client, calibration_set_id=calibration_set_id)
