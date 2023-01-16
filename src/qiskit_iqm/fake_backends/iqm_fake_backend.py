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

# pylint: disable=no-name-in-module,import-error,super-init-not-called,too-many-instance-attributes
"""
Qiskit fake backend for IQM quantum computers.
"""

from typing import Union

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, Measure, RGate
from qiskit.providers import JobV1
from qiskit.transpiler import Target
from qiskit.transpiler.coupling import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.noise.errors import depolarizing_error, thermal_relaxation_error

from qiskit_iqm.fake_backends.chip_sample import IQMChipSample
from qiskit_iqm.iqm_backend import IQMBackend

from .quantum_architectures import Adonis


class IQMFakeBackend(IQMBackend):
    """
    A fake backend class for an IQM chip sample.

    Args:
        chip_sample: An instance of a :class:`IQMChipSample` describing the
        characteristics of a specific chip sample.
    """

    def __init__(self, chip_sample: IQMChipSample, **kwargs):
        super(IQMBackend, self).__init__(self, **kwargs)

        if chip_sample is None:
            raise ValueError("No chip_sample provided.")

        self.chip_sample = chip_sample

        self.basis_1_qubit_gates = list(self.chip_sample.one_qubit_gate_depolarization_rates.keys())
        self.basis_2_qubit_gates = list(self.chip_sample.two_qubit_gate_depolarization_rates.keys())
        self.basis_gates = self.basis_1_qubit_gates + self.basis_2_qubit_gates

        # qubit_connectivity map, used for CouplingMap
        self.qubit_connectivity = []
        if len(self.basis_2_qubit_gates) > 0:
            gate_name = self.basis_2_qubit_gates[0]
            connections = self.chip_sample.two_qubit_gate_depolarization_rates[gate_name]
            # pylint: disable=unnecessary-lambda
            self.qubit_connectivity = list(map(lambda x: list(x), list(connections.keys())))
            # pylint: enable=unnecessary-lambda

        target = Target()
        target.add_instruction(
            RGate(Parameter("theta"), Parameter("phi")),
            {(qb,): None for qb in range(self.chip_sample.number_of_qubits)},
        )
        target.add_instruction(CZGate(), {(qb1, qb2): None for qb1, qb2 in self.qubit_connectivity})
        target.add_instruction(Measure(), {(qb,): None for qb in range(self.chip_sample.number_of_qubits)})
        self._target = target

        self.noise_model = self._create_noise_model()

    def _create_noise_model(self) -> NoiseModel:
        """
        Compiles a noise model from attributes of this instance of IQMSimulator.
        """
        noise_model = NoiseModel(basis_gates=self.basis_gates)

        # Add single-qubit gate errors to noise model
        for gate in self.basis_1_qubit_gates:
            for i in range(self.chip_sample.number_of_qubits):
                thermal_relaxation_channel = thermal_relaxation_error(
                    self.chip_sample.t1s[i], self.chip_sample.t2s[i], self.chip_sample.one_qubit_gate_durations[gate]
                )
                depolarizing_channel = depolarizing_error(
                    self.chip_sample.one_qubit_gate_depolarization_rates[gate][i], 1
                )
                full_error_channel = thermal_relaxation_channel.compose(depolarizing_channel)
                noise_model.add_quantum_error(full_error_channel, gate, [i])

        # Add two-qubit gate errors to noise model
        for gate in self.basis_2_qubit_gates:
            for connection in list(self.chip_sample.two_qubit_gate_depolarization_rates[gate].keys()):
                first_qubit = connection[0]
                second_qubit = connection[1]

                thermal_relaxation_channel = thermal_relaxation_error(
                    self.chip_sample.t1s[first_qubit],
                    self.chip_sample.t2s[first_qubit],
                    self.chip_sample.two_qubit_gate_durations[gate],
                ).tensor(
                    thermal_relaxation_error(
                        self.chip_sample.t1s[second_qubit],
                        self.chip_sample.t2s[second_qubit],
                        self.chip_sample.two_qubit_gate_durations[gate],
                    )
                )
                depolarizing_channel = depolarizing_error(
                    self.chip_sample.two_qubit_gate_depolarization_rates[gate][connection], 2
                )
                full_error_channel = thermal_relaxation_channel.compose(depolarizing_channel)
                noise_model.add_quantum_error(full_error_channel, gate, [first_qubit, second_qubit])

        return noise_model

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
            JobV1: The job object for the run
        Raises:
            ValueError: If empty list of circuits is provided.
        """
        circuits = [run_input] if isinstance(run_input, QuantumCircuit) else run_input

        if len(circuits) == 0:
            raise ValueError("Empty list of circuits submitted for execution.")

        shots = options.get("shots", self.options.shots)

        # COUPLING MAP
        coupling_map = CouplingMap(self.qubit_connectivity)
        # otherwise it would throw an error in the transpiler that Flipping gate direction is not supported for CPhase
        coupling_map.make_symmetric()

        # Create noisy simulator backend and run circuits
        sim_noise = AerSimulator(noise_model=self.noise_model, coupling_map=coupling_map, basis_gates=self.basis_gates)
        job = sim_noise.run(circuits, shots=shots)

        return job


class IQMFakeAdonis(IQMFakeBackend):
    """
    A fake backend class for an IQM adonis.

    Args:
        chip_sample: An instance of a :class:`IQMChipSample` describing the
            characteristics of a specific chip sample.
        **kwargs: optional arguments to be passed to the parent Qiskit Backend initializer
    """

    def __init__(self, chip_sample=None, **kwargs):
        if chip_sample is None:
            chip_sample = adonis_chip_sample
        super().__init__(chip_sample, **kwargs)


adonis_chip_sample = IQMChipSample(
    quantum_architecture=Adonis(),
    t1s={0: 27000.0, 1: 33000.0, 2: 25000.0, 3: 40000.0, 4: 25000.0},
    t2s={0: 20000.0, 1: 26000.0, 2: 23000.0, 3: 26000.0, 4: 7000.0},
    one_qubit_gate_depolarization_rates={"r": {0: 0.0006, 1: 0.0054, 2: 0.0001, 3: 0.0, 4: 0.0005}},
    two_qubit_gate_depolarization_rates={"cz": {(0, 2): 0.0335, (1, 2): 0.0344, (3, 2): 0.0192, (4, 2): 0.0373}},
    one_qubit_gate_durations={"r": 40.0},
    two_qubit_gate_durations={"cz": 80.0},
    id_="sample-chip",
)
