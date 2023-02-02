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
"""Testing IQM fake backend.
"""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.compiler import transpile
from qiskit.providers import JobV1
from qiskit_aer import noise

from qiskit_iqm import IQMFakeBackend


@pytest.fixture
def backend(create_chip_sample):
    return IQMFakeBackend(create_chip_sample())


def test_run_single_circuit(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    shots = 10
    job = backend.run(circuit, qubit_mapping=None, shots=shots)
    assert isinstance(job, JobV1)
    assert job.result() is not None

    # Should also work if the circuit is passed inside a list
    job = backend.run([circuit], qubit_mapping=None, shots=shots)
    assert isinstance(job, JobV1)
    assert job.result() is not None


def test_run_with_non_default_settings(backend):
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    shots = 10
    settings = {"setting1": 5}

    job = backend.run([circuit], qubit_mapping=None, settings=settings, shots=shots)
    assert isinstance(job, JobV1)
    assert job.result() is not None


def test_run_batch_of_circuits(backend):
    qc = QuantumCircuit(2)
    theta = Parameter("theta")
    theta_range = np.linspace(0, 2 * np.pi, 3)
    shots = 10
    qc.cz(0, 1)
    qc.r(theta, 0, 0)
    qc.cz(0, 1)
    circuits = [qc.bind_parameters({theta: t}) for t in theta_range]

    job = backend.run(circuits, qubit_mapping={qc.qubits[0]: "QB1", qc.qubits[1]: "QB2"}, shots=shots)
    assert isinstance(job, JobV1)
    assert job.result() is not None


def test_error_on_empty_circuit_list(backend):
    with pytest.raises(ValueError, match="Empty list of circuits submitted for execution."):
        backend.run([], qubit_mapping={}, shots=42)


def test_noise_model_is_valid(backend):
    """
    Tests if noise model of a fake backend is a Qiskit noise model object.
    """
    noise_model = backend.noise_model
    assert isinstance(noise_model, noise.NoiseModel)


def test_noise_on_all_qubits(backend):
    """
    Tests if noise is applied to all qubits of the device.
    """
    noise_model = backend.noise_model

    simulator_qubit_indices = list(range(backend.num_qubits))
    noisy_qubits = noise_model.noise_qubits

    assert simulator_qubit_indices == noisy_qubits


def test_noise_model_has_noise_terms(backend):
    """
    Tests if the noise model has some noise terms, i.e., tests if the noise model
    doesn't have no noise terms.
    """
    noise_model = backend.noise_model

    assert not noise_model.is_ideal()


def test_noisy_bell_state(backend):
    """
    Tests if a generated Bell state is noisy.
    """
    circ = QuantumCircuit(2)
    circ.h(0)
    circ.cx(0, 1)
    circ.measure_all()

    transpiled_circuit = transpile(circ, backend=backend)
    job = backend.run(transpiled_circuit, shots=10000)
    counts = job.result().get_counts()

    wrong_results = 0
    if "01" in counts:
        wrong_results += counts["01"]
    if "10" in counts:
        wrong_results += counts["10"]
    assert wrong_results > 0
