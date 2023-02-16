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
import pytest
from qiskit import QuantumCircuit
from qiskit.providers import JobV1
from qiskit_aer.noise.noise_model import NoiseModel

from qiskit_iqm import IQMFakeBackend


@pytest.fixture
def backend(create_chip_sample):
    return IQMFakeBackend(create_chip_sample())


def test_iqm_fake_backend_noise_model_instantiated(backend):
    """Test that creating a Fake Backend instantiates a Qiskit noise model"""
    assert isinstance(backend.noise_model, NoiseModel)


def test_iqm_fake_backend_noise_model_basis_gates(backend):
    """Test that all operations named as part of the backend are utilizes in the noise_model"""
    assert all(gates in backend.operation_names for gates in backend.noise_model.basis_gates)


def test_run_single_circuit(backend):
    """Test that the backend can be called with a circuit
    or a list of circuits and returns a result."""
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


def test_error_on_empty_circuit_list(backend):
    """Test that calling run with an empty list of circuits raises a ValueError."""
    with pytest.raises(ValueError, match="Empty list of circuits submitted for execution."):
        backend.run([], qubit_mapping=None)


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
