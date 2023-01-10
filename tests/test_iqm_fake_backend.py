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
import collections
from unittest.mock import patch

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.compiler import transpile
from qiskit.providers import JobV1
from qiskit_aer import noise

from qiskit_iqm import IQMFakeAdonis, IQMFakeBackend
from qiskit_iqm.fake_backends.chip_sample import IQMChipSample
from qiskit_iqm.fake_backends.quantum_architectures import Adonis, IQMQuantumArchitecture


@pytest.fixture
def backend():
    sample = IQMChipSample(
        quantum_architecture=Adonis(),
        t1s=[29000.0, 33000.0, 25000.0, 40000.0, 25000.0],
        t2s=[20000.0, 26000.0, 23000.0, 26000.0, 7000.0],
        one_qubit_gate_fidelities={"r": {0: 0.9988, 1: 0.9966, 2: 0.9991, 3: 0.9994, 4: 0.9976}},
        two_qubit_gate_fidelities={"cz": {(0, 2): 0.9708, (1, 2): 0.9706, (3, 2): 0.982, (4, 2): 0.9651}},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0006, 1: 0.0054, 2: 0.0001, 3: 0.0, 4: 0.0005}},
        two_qubit_gate_depolarization_rates={"cz": {(0, 2): 0.0335, (1, 2): 0.0344, (3, 2): 0.0192, (4, 2): 0.0373}},
        one_qubit_gate_durations={"r": 40.0},
        two_qubit_gate_durations={"cz": 80.0},
        id_="adonis-example_sample",
    )

    return IQMFakeBackend(sample)


@pytest.fixture
def ThreeQubitExample():
    class ThreeQubitExample(IQMQuantumArchitecture):
        """Class implementation for IQMs 5-qubit QPU architecture."""

        def __init__(self):
            super().__init__(
                number_of_qubits=3,
                topology=[[0, 1], [1, 2]],
                basis_one_qubit_gates=["r"],
                basis_two_qubit_gates=[],
                id_="sample-three-qubit-architecture",
            )

    return ThreeQubitExample


def test_warning_raised_if_no_config_provided():
    with pytest.raises(Exception):
        IQMFakeBackend(chip_sample=None)


def test_chip_sample_with_no_2_qubit_gates_specified():
    sample = IQMChipSample(
        quantum_architecture=Adonis(),
        t1s=[50000] * 5,
        t2s=[50000] * 5,
        one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.999, 2: 0.999, 3: 0.999, 4: 0.999}},
        two_qubit_gate_fidelities={},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0001, 1: 0.0001, 2: 0, 3: 0, 4: 0.0001}},
        two_qubit_gate_depolarization_rates={},
        one_qubit_gate_durations={"r": 1.0},
        two_qubit_gate_durations={},
        id_="adonis-example_sample",
    )

    backend = IQMFakeBackend(sample)
    assert len(backend.qubit_connectivity) == 0


def test_iqm_fake_adonis():
    backend = IQMFakeAdonis()
    assert backend.number_of_qubits == 5


def test_iqm_fake_adonis_with_chip_sample():
    sample = IQMChipSample(
        quantum_architecture=Adonis(),
        t1s={0: 42, 1: 42, 2: 42, 3: 42, 4: 42},
        t2s={0: 42, 1: 42, 2: 42, 3: 42, 4: 42},
        one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.999, 2: 0.999, 3: 0.999, 4: 0.999}},
        two_qubit_gate_fidelities={"cz": {(0, 2): 0.999, (1, 2): 0.999, (3, 2): 0.999, (4, 2): 0.999}},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0001, 1: 0.0001, 2: 0.0001, 3: 0.0001, 4: 0.0001}},
        two_qubit_gate_depolarization_rates={"cz": {(0, 2): 0.001, (1, 2): 0.001, (3, 2): 0.001, (4, 2): 0.001}},
        one_qubit_gate_durations={"r": 40.0},
        two_qubit_gate_durations={"cz": 80.0},
        id_="sample-chip",
    )

    backend = IQMFakeAdonis(chip_sample=sample)
    assert backend.t1s[0] == 42


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


def test_basis_gates(backend):
    """
    Tests if basis gates of noise model and IQMSimulator are the same.
    """
    noise_model = backend.noise_model

    assert collections.Counter(backend.basis_gates) == collections.Counter(noise_model.noise_instructions)


def test_noise_on_all_qubits(backend):
    """
    Tests if noise is applied to all qubits of the device.
    """
    noise_model = backend.noise_model

    simulator_qubit_indices = list(range(backend.number_of_qubits))
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

    transpiled_circuit = transpile(circ, basis_gates=backend.basis_gates)
    job = backend.run(transpiled_circuit, shots=10000)
    counts = job.result().get_counts()

    wrong_results = 0
    if "01" in counts:
        wrong_results += counts["01"]
    if "10" in counts:
        wrong_results += counts["10"]
    assert wrong_results > 0


def test_chip_sample_check_if_parameters_are_validated(ThreeQubitExample):
    with patch.object(IQMChipSample, "_validate_parameters", return_value=True) as mock_method:
        IQMChipSample(
            quantum_architecture=ThreeQubitExample(),
            t1s={0: 10000.0, 1: 12000.0},
            t2s={0: 10000.0, 1: 12000.0, 2: 13000.0},
            one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.996, 2: 0.998}},
            two_qubit_gate_fidelities={},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
            two_qubit_gate_depolarization_rates={},
            one_qubit_gate_durations={"r": 50.0},
            two_qubit_gate_durations={},
        )

    mock_method.assert_called_once()


def test_chip_sample_validation_to_few_t1_times_provided(ThreeQubitExample):
    with pytest.raises(ValueError):

        IQMChipSample(
            quantum_architecture=ThreeQubitExample(),
            t1s={0: 10000.0, 1: 12000.0},
            t2s={0: 10000.0, 1: 12000.0, 2: 13000.0},
            one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.996, 2: 0.998}},
            two_qubit_gate_fidelities={},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
            two_qubit_gate_depolarization_rates={},
            one_qubit_gate_durations={"r": 50.0},
            two_qubit_gate_durations={},
        )


def test_chip_sample_validation_to_few_t2_times_provided(ThreeQubitExample):
    with pytest.raises(ValueError):

        IQMChipSample(
            quantum_architecture=ThreeQubitExample(),
            t1s={0: 10000.0, 1: 12000.0, 2: 1337},
            t2s={0: 10000.0, 1: 12000.0},
            one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.996, 2: 0.998}},
            two_qubit_gate_fidelities={},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
            two_qubit_gate_depolarization_rates={},
            one_qubit_gate_durations={"r": 50.0},
            two_qubit_gate_durations={},
        )


def test_chip_sample_validation_1qubit_fidelities_dict_entries_match_qubits(ThreeQubitExample):

    IQMChipSample(
        quantum_architecture=ThreeQubitExample(),
        t1s={0: 10000.0, 1: 12000.0, 2: 1337},
        t2s={0: 10000.0, 1: 12000.0, 2: 1337},
        one_qubit_gate_fidelities={"r": {0: 0.999, 1: 12000.0, 2: 1337}},
        two_qubit_gate_fidelities={},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
        two_qubit_gate_depolarization_rates={},
        one_qubit_gate_durations={"r": 50.0},
        two_qubit_gate_durations={},
    )

    with pytest.raises(ValueError):

        IQMChipSample(
            quantum_architecture=ThreeQubitExample(),
            t1s={0: 10000.0, 1: 12000.0, 2: 1337},
            t2s={0: 10000.0, 1: 12000.0, 2: 1337},
            one_qubit_gate_fidelities={"r": {5: 0.999, 1: 12000.0, 2: 1337}},
            two_qubit_gate_fidelities={},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
            two_qubit_gate_depolarization_rates={},
            one_qubit_gate_durations={"r": 50.0},
            two_qubit_gate_durations={},
        )


def test_chip_sample_validation_2qubit_gate_not_supported_by_architecture(ThreeQubitExample):

    IQMChipSample(
        quantum_architecture=ThreeQubitExample(),
        t1s={0: 10000.0, 1: 12000.0, 2: 14000.0},
        t2s={0: 10000.0, 1: 12000.0, 2: 13000.0},
        one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.996, 2: 0.998}},
        two_qubit_gate_fidelities={},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
        two_qubit_gate_depolarization_rates={},
        one_qubit_gate_durations={"r": 50.0},
        two_qubit_gate_durations={},
        id_="threequbit-example_sample",
    )

    with pytest.raises(ValueError):

        IQMChipSample(
            quantum_architecture=ThreeQubitExample(),
            t1s={0: 10000.0, 1: 12000.0, 2: 14000.0},
            t2s={0: 10000.0, 1: 12000.0, 2: 13000.0},
            one_qubit_gate_fidelities={"x": {0: 0.999, 1: 0.996, 2: 0.998}},
            two_qubit_gate_fidelities={},
            one_qubit_gate_depolarization_rates={"x": {0: 0.0005, 1: 0.0004, 2: 0.0010}},
            two_qubit_gate_depolarization_rates={},
            one_qubit_gate_durations={"x": 50.0},
            two_qubit_gate_durations={},
            id_="threequbit-example_sample",
        )


def test_chip_sample_validation_2qubit_gate_has_wrong_connections():
    IQMChipSample(
        quantum_architecture=Adonis(),
        t1s={0: 50000.0, 1: 50000.0, 2: 50000.0, 3: 50000.0, 4: 50000.0},
        t2s={0: 50000.0, 1: 50000.0, 2: 50000.0, 3: 50000.0, 4: 50000.0},
        one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.999, 2: 0.999, 3: 0.999, 4: 0.999}},
        two_qubit_gate_fidelities={"cz": {(0, 2): 0.999, (1, 2): 0.999, (3, 2): 0.999, (4, 2): 0.999}},
        one_qubit_gate_depolarization_rates={"r": {0: 0.0001, 1: 0.0001, 2: 0.0001, 3: 0.0001, 4: 0.0001}},
        two_qubit_gate_depolarization_rates={"cz": {(0, 2): 0.001, (1, 2): 0.001, (3, 2): 0.001, (4, 2): 0.001}},
        one_qubit_gate_durations={"r": 40.0},
        two_qubit_gate_durations={"cz": 80.0},
        id_="sample-chip",
    )

    with pytest.raises(ValueError):

        IQMChipSample(
            quantum_architecture=Adonis(),
            t1s={0: 50000.0, 1: 50000.0, 2: 50000.0, 3: 50000.0, 4: 50000.0},
            t2s={0: 50000.0, 1: 50000.0, 2: 50000.0, 3: 50000.0, 4: 50000.0},
            one_qubit_gate_fidelities={"r": {0: 0.999, 1: 0.999, 2: 0.999, 3: 0.999, 4: 0.999}},
            two_qubit_gate_fidelities={"cz": {(0, 2): 0.999, (1, 2): 0.999, (3, 2): 0.999, (4, 2): 0.999}},
            one_qubit_gate_depolarization_rates={"r": {0: 0.0001, 1: 0.0001, 2: 0.0001, 3: 0.0001, 4: 0.0001}},
            two_qubit_gate_depolarization_rates={"cz": {(42, 2): 0.001, (1, 2): 0.001, (3, 2): 0.001, (4, 2): 0.001}},
            one_qubit_gate_durations={"r": 40.0},
            two_qubit_gate_durations={"cz": 80.0},
            id_="sample-chip",
        )
