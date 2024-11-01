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

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMFakeBackend


@pytest.fixture
def backend(linear_3q_architecture_static, create_3q_error_profile):
    return IQMFakeBackend(linear_3q_architecture_static, create_3q_error_profile())


def test_fake_backend_with_incomplete_t1s(linear_3q_architecture_static, create_3q_error_profile):
    """Test that IQMFakeBackend construction fails if T1 times are not provided for all qubits"""
    with pytest.raises(ValueError, match="Length of t1s"):
        error_profile = create_3q_error_profile(t1s={"QB1": 2000, "QB3": 2000})
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_fake_backend_with_incomplete_t2s(linear_3q_architecture_static, create_3q_error_profile):
    """Test that IQMFakeBackend construction fails if T2 times are not provided for all qubits"""
    with pytest.raises(ValueError, match="Length of t2s"):
        error_profile = create_3q_error_profile(t2s={"QB1": 2000, "QB3": 2000})
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_fake_backend_with_single_qubit_gate_depolarizing_errors_qubits_not_matching_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
):
    """Test that IQMFakeBackend construction fails if depolarizing rates are not provided for all qubits"""
    with pytest.raises(ValueError, match="The qubits specified for one-qubit gate"):
        error_profile = create_3q_error_profile(
            single_qubit_gate_depolarizing_error_parameters={"prx": {"QB1": 0.0001, "QB2": 0.0001}},
        )
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_fake_backend_with_single_qubit_gate_depolarizing_errors_more_qubits_than_in_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
):
    """Test that IQMFakeBackend construction fails if depolarizing rates are provided for
    other qubits than specified in the quantum architecture"""
    with pytest.raises(ValueError, match="The qubits specified for one-qubit gate"):
        error_profile = create_3q_error_profile(
            single_qubit_gate_depolarizing_error_parameters={
                "prx": {"QB1": 0.0001, "QB2": 0.0001, "QB3": 0.0001, "QB4": 0.0001}
            },
        )
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_fake_backend_with_two_qubit_gate_depolarizing_errors_couplings_not_matching_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
):
    """Test that IQMFakeBackend construction fails if depolarizing rates are
    not provided for all couplings of the quantum architecture (QB1 -- QB2 -- QB3 here)"""
    with pytest.raises(ValueError, match="The couplings specified for two-qubit gate"):
        error_profile = create_3q_error_profile(
            two_qubit_gate_depolarizing_error_parameters={"cz": {("QB1", "QB2"): 0.001}},
        )
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_fake_backend_with_two_qubit_gate_depolarizing_errors_more_couplings_than_in_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
):
    """Test that IQMFakeBackend construction fails if depolarizing rates are provided for
    other couplings than specified in the quantum architecture"""
    with pytest.raises(ValueError, match="The couplings specified for two-qubit gate"):
        error_profile = create_3q_error_profile(
            two_qubit_gate_depolarizing_error_parameters={
                "cz": {("QB1", "QB2"): 0.001, ("QB2", "QB3"): 0.001, ("QB1", "QB3"): 0.001}
            },
        )
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


@pytest.mark.parametrize(
    "param_name,param_value",
    [
        (
            "single_qubit_gate_depolarizing_error_parameters",
            {"wrong": {"QB1": 0.0001, "QB2": 0.0001, "QB3": 0}},
        ),
        (
            "two_qubit_gate_depolarizing_error_parameters",
            {"wrong": {("QB1", "QB2"): 0.001, ("QB2", "QB3"): 0.001}},
        ),
    ],
)
def test_fake_backend_not_matching_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
    param_name: str,
    param_value: dict,
):
    """Test that IQMFakeBackend construction fails if one qubit depolarizing rates are
    refering to a gate not available in quantum architecture"""
    with pytest.raises(
        ValueError,
        match=f"Gate `wrong` in `{param_name}` is not supported",
    ):
        error_profile = create_3q_error_profile(**{param_name: param_value})
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_error_profile(linear_3q_architecture_static, create_3q_error_profile):
    err_profile = create_3q_error_profile()
    backend = IQMFakeBackend(linear_3q_architecture_static, err_profile)

    assert backend.error_profile == err_profile

    # Assert that error profile cannot be modified
    backend.error_profile.t1s["QB1"] = backend.error_profile.t1s["QB1"] + 127
    assert backend.error_profile == err_profile


def test_set_error_profile(backend, create_3q_error_profile):
    with pytest.raises(NotImplementedError, match="Setting error profile of existing fake backend is not allowed."):
        backend.error_profile = create_3q_error_profile()


def test_copy_with_error_profile(linear_3q_architecture_static, create_3q_error_profile):
    err_profile = create_3q_error_profile()
    backend = IQMFakeBackend(linear_3q_architecture_static, err_profile)

    new_t1s = err_profile.t1s
    new_t1s["QB1"] = new_t1s["QB1"] + 128
    new_err_profile = create_3q_error_profile(t1s=new_t1s)
    new_backend = backend.copy_with_error_profile(new_err_profile)
    assert new_backend.error_profile == new_err_profile


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


def test_fake_backend_with_readout_errors_more_qubits_than_in_quantum_architecture(
    linear_3q_architecture_static,
    create_3q_error_profile,
):
    """Test that IQMFakeBackend construction fails if readout errors are provided for
    other qubits than specified in the quantum architecture"""
    with pytest.raises(ValueError, match="The qubits specified in readout errors"):
        error_profile = create_3q_error_profile(
            readout_errors={
                "QB1": {"0": 0.02, "1": 0.03},
                "QB2": {"0": 0.02, "1": 0.03},
                "QB4": {"0": 0.02, "1": 0.03},
            },
        )
        IQMFakeBackend(linear_3q_architecture_static, error_profile)


def test_noise_model_contains_all_errors(backend):
    """
    Test that the noise model contains all necessary errors.
    """
    assert set(backend.noise_model.noise_instructions) == {"r", "cz", "measure"}

    # Assert that CZ gate error is applied independent of argument order in gate specification
    assert set(backend.noise_model._local_quantum_errors["cz"].keys()) == set([(0, 1), (1, 0), (1, 2), (2, 1)])


def test_validate_compatible_architecture(
    adonis_architecture, adonis_shuffled_names_architecture, linear_3q_architecture
):
    backend = IQMFakeAdonis()
    assert backend.validate_compatible_architecture(adonis_architecture) is True
    assert backend.validate_compatible_architecture(adonis_shuffled_names_architecture) is True
    assert backend.validate_compatible_architecture(linear_3q_architecture) is False
