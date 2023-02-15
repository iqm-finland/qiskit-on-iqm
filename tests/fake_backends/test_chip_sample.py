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

"""Testing IQM Chip sample.
"""
import pytest


def test_chip_sample_with_incomplete_t1s(create_chip_sample):
    """Test that ChipSample construction fails if T1 times are not provided for all qubits"""
    with pytest.raises(ValueError, match="Length of t1s"):
        create_chip_sample(t1s={"QB1": 2000, "QB3": 2000})


def test_chip_sample_with_incomplete_t2s(create_chip_sample):
    """Test that ChipSample construction fails if T2 times are not provided for all qubits"""
    with pytest.raises(ValueError, match="Length of t2s"):
        create_chip_sample(t2s={"QB1": 2000, "QB3": 2000})


def test_chip_sample_with_one_qubit_depolarization_rates_qubits_not_matching_quantum_architecture(create_chip_sample):
    """Test that ChipSample construction fails if depolarization rates are not provided for all qubits"""
    with pytest.raises(ValueError, match="The qubits specified for one-qubit gate"):
        create_chip_sample(
            one_qubit_gate_depolarization_rates={"phased_rx": {"QB1": 0.0001, "QB2": 0.0001}},
        )


def test_chip_sample_with_one_qubit_depolarization_rates_more_qubits_than_in_quantum_architecture(create_chip_sample):
    """Test that ChipSample construction fails if depolarization rates are provided for
    other qubits than specified in the quantum architecture"""
    with pytest.raises(ValueError, match="The qubits specified for one-qubit gate"):
        create_chip_sample(
            one_qubit_gate_depolarization_rates={
                "phased_rx": {"QB1": 0.0001, "QB2": 0.0001, "QB3": 0.0001, "QB4": 0.0001}
            },
        )


def test_chip_sample_with_two_qubits_depolarization_rates_couplings_not_matching_quantum_architecture(
    create_chip_sample,
):
    """Test that ChipSample construction fails if depolarization rates are
    not provided for all couplings of the quantum architecture (QB1 -- QB2 -- QB3 here)"""
    with pytest.raises(ValueError, match="The couplings specified for two-qubit gate"):
        create_chip_sample(
            two_qubit_gate_depolarization_rates={"cz": {("QB1", "QB2"): 0.001}},
        )


def test_chip_sample_with_two_qubits_depolarization_rates_more_couplings_than_in_quantum_architecture(
    create_chip_sample,
):
    """Test that ChipSample construction fails if depolarization rates are provided for
    other couplings than specified in the quantum architecture"""
    with pytest.raises(ValueError, match="The couplings specified for two-qubit gate"):
        create_chip_sample(
            two_qubit_gate_depolarization_rates={
                "cz": {("QB1", "QB2"): 0.001, ("QB2", "QB3"): 0.001, ("QB1", "QB3"): 0.001}
            },
        )


def test_chip_sample_with_one_qubit_depolarization_rates_gate_name_not_matching_quantum_architecture(
    create_chip_sample,
):
    """Test that ChipSample construction fails if one qubit depolarization rates are
    refering to a gate not available in quantum architecture"""
    with pytest.raises(
        ValueError, match="Gate `rxnotexistent` in `gate_one qubit gate depolarization_rates` is not supported"
    ):
        create_chip_sample(
            one_qubit_gate_depolarization_rates={"rxnotexistent": {"QB1": 0.0001, "QB2": 0.0001, "QB3": 0}},
        )


def test_chip_sample_with_two_qubits_depolarization_rates_gate_name_not_matching_quantum_architecture(
    create_chip_sample,
):
    """Test that ChipSample construction fails if two qubit depolarization rates are
    refering to a gate not available in quantum architecture"""
    with pytest.raises(
        ValueError, match="Gate `cnotexistent` in `gate_two qubit gate depolarization_rates` is not supported"
    ):
        create_chip_sample(
            two_qubit_gate_depolarization_rates={"cnotexistent": {("QB1", "QB2"): 0.001, ("QB2", "QB3"): 0.001}},
        )
