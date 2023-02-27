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

# pylint: disable=too-many-instance-attributes
"""Abstract representation of an IQM chip sample.
"""
from dataclasses import dataclass
from typing import Any, Union

from iqm_client import QuantumArchitectureSpecification


@dataclass
class IQMChipSample:
    """Physical properties of a quantum chip sample.

    Args:
        quantum_architecture: Quantum architecture specification of the chip.
        t1s: :math:`T_1` times (in ns) for each qubit of the chip, corresponding key is the physical qubit name.
        t2s: :math:`T_2` times (in ns) for each qubit of the chip, corresponding key is the physical qubit name.
        single_qubit_gate_depolarizing_error_parameters: Depolarizing error parameters for single-qubit gates of each
            qubit. Using the values in the depolarizing channel, concatenated with a thermal relaxation channel,
            lead to average gate fidelities that would be determined by benchmarking.
        two_qubit_gate_depolarizing_error_parameters: Depolarizing error parameters for two-qubit gates of each
            connection. Using the values in the depolarizing channel, concatenated with a thermal relaxation channel,
            lead to average gate fidelities that would be determined by benchmarking.
        single_qubit_gate_durations: Gate duration (in ns) for each single-qubit gate
        two_qubit_gate_durations: Gate duration (in ns) for each two-qubit gate.
        id_: Identifier of the chip sample. Defaults to None.

    Example:
        .. code-block::

            linear_architecture_3q=QuantumArchitectureSpecification(
                name="Example",
                operations=["phased_rx", "cz", "measurement", "barrier"],
                qubits=["QB1", "QB2", "QB3"],
                qubit_connectivity=[["QB1", "QB2"], ["QB2", "QB3"]],
            ),

            IQMChipSample(quantum_architecture=linear_architecture_3q,
                        t1s={"QB1": 10000.0, "QB2": 12000.0, "QB3": 14000.0},
                        t2s={"QB1": 10000.0, "QB2": 12000.0, "QB3": 13000.0},
                        single_qubit_gate_depolarizing_error_parameters={"r": {"QB1": 0.0005,
                                                                    "QB2": 0.0004,
                                                                    "QB3": 0.0010}},
                        two_qubit_gate_depolarizing_error_parameters={"cz": {("QB1", "QB2"): 0.08,
                                                                    ("QB2", "QB3"): 0.03}},
                        one_qubit_gate_durations={"r": 50.},
                        two_qubit_gate_durations={"cz": 100.},
                        id_="threequbit-example_sample")
    """
    quantum_architecture: QuantumArchitectureSpecification
    t1s: dict[str, float]
    t2s: dict[str, float]
    single_qubit_gate_depolarizing_error_parameters: dict[str, dict[str, float]]
    two_qubit_gate_depolarizing_error_parameters: dict[str, dict[tuple[str, str], float]]
    single_qubit_gate_durations: dict[str, float]
    two_qubit_gate_durations: dict[str, float]
    id_: Union[str, None] = None

    def __post_init__(self):
        self._validate_parameters()

    @property
    def number_of_qubits(self) -> int:
        """Get the number of qubits"""
        return len(self.quantum_architecture.qubits)

    @property
    def gate_durations(self) -> dict[str, float]:
        """get all gate durations"""
        return self.single_qubit_gate_durations | self.two_qubit_gate_durations

    def _validate_parameters(self) -> None:
        """Verifies that the parameters of the chip sample match the constraints of its IQMQuantumArchitecture.

        Raises:
            ValueError: when length of `t1s` and number of qubits do not match.
            ValueError: when length of `t2s` and number of qubits do not match.
            ValueError: when length of `one_qubit_gate` parameter lists and number of qubits do not match.
            ValueError: when length of `two_qubit_gate` parameter lists and number of couplings do not match.
            ValueError: when gates in gate parameter lists are not supported by the quantum architecture.
        """
        num_qubits = len(self.quantum_architecture.qubits)
        # Check that T1 list has one element for each qubit
        if len(self.t1s) != num_qubits:
            raise ValueError(f"Length of t1s ({len(self.t1s)}) and number of qubits ({num_qubits}) should match.")

        # Check that T2 list has one element for each qubit
        if len(self.t2s) != num_qubits:
            raise ValueError(f"Length of t2s ({len(self.t2s)}) and number of qubits ({num_qubits}) should match.")

        property_dict: dict[str, dict[Any, float]]
        # Check that one-qubit gate parameter qubits match those of the architecture
        for property_name, property_dict in [
            ("depolarizing rates", self.single_qubit_gate_depolarizing_error_parameters),
        ]:
            gate_dict: dict[Any, float]
            for gate, gate_dict in property_dict.items():
                if set(gate_dict.keys()) != set(self.quantum_architecture.qubits):
                    raise ValueError(
                        (
                            f"The qubits specified for one-qubit gate {property_name} ({set(gate_dict.keys())}) "
                            f"don't match the qubits of the quantum architecture "
                            f"`{self.quantum_architecture.name}` "
                            f"({self.quantum_architecture.qubits})."
                        )
                    )

        # Check that two-qubit gate parameter couplings match those of the architecture
        for property_name, property_dict in [
            ("depolarizing error parameters", self.two_qubit_gate_depolarizing_error_parameters),
        ]:
            for gate, gate_dict in property_dict.items():
                if set(gate_dict.keys()) != set(tuple(item) for item in self.quantum_architecture.qubit_connectivity):
                    raise ValueError(
                        (
                            f"The couplings specified for two-qubit gate {property_name} ({set(gate_dict.keys())}) "
                            f"don't match the couplings of the quantum architecture "
                            f"`{self.quantum_architecture.name}` ({self.quantum_architecture.qubit_connectivity})."
                        )
                    )

        # Check that the basis gates of the chip sample match the quantum architecture's
        for property_name, specified_gates in [
            (
                "single qubit gate depolarizing_error_parameters",
                self.single_qubit_gate_depolarizing_error_parameters.keys(),
            ),
            ("two qubit gate depolarizing_error_parameters", self.two_qubit_gate_depolarizing_error_parameters.keys()),
            ("durations", self.gate_durations.keys()),
        ]:
            for gate in specified_gates:
                if gate not in self.quantum_architecture.operations:
                    raise ValueError(
                        (
                            f"Gate `{gate}` in `gate_{property_name}` "
                            "is not supported by quantum architecture `{self.quantum_architecture.id_}`. "
                            f"Valid gates: {self.quantum_architecture.operations}"
                        )
                    )
