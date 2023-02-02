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

# pylint: disable=no-name-in-module,import-error,super-init-not-called,too-many-instance-attributes
"""
Fake backend for simulating IQM quantum computers.
"""

from typing import Optional, Union

from qiskit import QuantumCircuit
from qiskit.providers import JobV1, Options
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.noise.errors import depolarizing_error, thermal_relaxation_error

from qiskit_iqm.fake_backends.chip_sample import IQMChipSample
from qiskit_iqm.iqm_backend import IQMBackendBase, IQM_TO_QISKIT_GATE_NAME


class IQMFakeBackend(IQMBackendBase):
    """
    Fake backend for simulating an IQM QPU.

    Args:
        chip_sample: Describes the characteristics of a specific chip sample.
    """

    def __init__(self, chip_sample: IQMChipSample, **kwargs):
        super().__init__(chip_sample.quantum_architecture, **kwargs)
        self.noise_model = self._create_noise_model(chip_sample)

    def _create_noise_model(self, chip_sample: IQMChipSample) -> NoiseModel:
        """
        Builds a noise model from the attributes.
        """
        noise_model = NoiseModel(basis_gates=['r', 'cz'])

        # Add single-qubit gate errors to noise model
        for gate in chip_sample.one_qubit_gate_depolarization_rates.keys():
            for qb in chip_sample.quantum_architecture.qubits:
                thermal_relaxation_channel = thermal_relaxation_error(
                    chip_sample.t1s[qb], chip_sample.t2s[qb], chip_sample.one_qubit_gate_durations[gate]
                )
                depolarizing_channel = depolarizing_error(
                    chip_sample.one_qubit_gate_depolarization_rates[gate][qb], 1
                )
                full_error_channel = thermal_relaxation_channel.compose(depolarizing_channel)
                noise_model.add_quantum_error(full_error_channel, IQM_TO_QISKIT_GATE_NAME[gate], [self.qubit_name_to_index(qb)])

        # Add two-qubit gate errors to noise model
        for gate in chip_sample.two_qubit_gate_depolarization_rates.keys():
            for connection in list(chip_sample.two_qubit_gate_depolarization_rates[gate].keys()):
                first_qubit, second_qubit = connection

                thermal_relaxation_channel = thermal_relaxation_error(
                    chip_sample.t1s[first_qubit],
                    chip_sample.t2s[first_qubit],
                    chip_sample.two_qubit_gate_durations[gate],
                ).tensor(
                    thermal_relaxation_error(
                        chip_sample.t1s[second_qubit],
                        chip_sample.t2s[second_qubit],
                        chip_sample.two_qubit_gate_durations[gate],
                    )
                )
                depolarizing_channel = depolarizing_error(
                    chip_sample.two_qubit_gate_depolarization_rates[gate][connection], 2
                )
                full_error_channel = thermal_relaxation_channel.compose(depolarizing_channel)
                noise_model.add_quantum_error(full_error_channel, IQM_TO_QISKIT_GATE_NAME[gate], [self.qubit_name_to_index(first_qubit), self.qubit_name_to_index(second_qubit)])

        return noise_model

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1024, calibration_set_id=None)

    @property
    def max_circuits(self) -> Optional[int]:
        return None

    def run(self, run_input: Union[QuantumCircuit, list[QuantumCircuit]], **options) -> JobV1:
        """
        Run `run_input` on the fake backend using a simulator.

        This method runs circuit jobs (an individual or a list of QuantumCircuit
        ) and returns a :class:`~qiskit.providers.JobV1` object.

        It will run the simulation with a noise model of the fake backend (e.g. Adonis).

        Args:
            run_input (QuantumCircuit or list of QuantumCircuit): An
                individual or a list of
                :class:`~qiskit.circuits.QuantumCircuit` objects to run on the backend.
            options: Any kwarg options to pass to the backend.
        Returns:
            The job object representing the run.
        Raises:
            ValueError: If empty list of circuits is provided.
        """
        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError("Empty list of circuits submitted for execution.")

        shots = options.get("shots", self.options.shots)

        # Create noisy simulator backend and run circuits
        sim_noise = AerSimulator(noise_model=self.noise_model)
        job = sim_noise.run(circuits, shots=shots)

        return job
