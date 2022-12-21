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

# pylint: disable=no-name-in-module,import-error,too-many-instance-attributes,too-many-arguments,line-too-long
"""Abstract representation of an IQM chip sample.
"""

from typing import Dict, List, Tuple, Union

from .quantum_architectures import IQMQuantumArchitecture


class IQMChipSample:
    """Class implementation to provide a abstract representation of
    the specifications of a IQM chip sample.
    """

    def __init__(
        self,
        quantum_architecture: IQMQuantumArchitecture,
        t1s: List[float],
        t2s: List[float],
        one_qubit_gate_fidelities: Dict[str, Dict[int, float]],
        two_qubit_gate_fidelities: Dict[str, Dict[Tuple[int, int], float]],
        one_qubit_gate_depolarization_rates: Dict[str, Dict[int, float]],
        two_qubit_gate_depolarization_rates: Dict[str, Dict[Tuple[int, int], float]],
        one_qubit_gate_durations: Dict[str, float],
        two_qubit_gate_durations: Dict[str, float],
        id_: Union[str, None] = None,
    ):
        """Provides the specifications of a quantum chip sample.

        Args:
            quantum_architecture (IQMQuantumArchitecture): an instance of a Quantum Architecture.
            t1s (List[float]): the list of T1 times, in ascending qubit index order.
            t2s (List[float]): the list of T2 times, in ascending qubit index order.
            one_qubit_gate_fidelities (Dict[str, Dict[int, float]]): for each one-qubit gate, a fidelity is specified
                for each qubit.
            two_qubit_gate_fidelities (Dict[str, Dict[Tuple[int], float]]): for each two-qubit gate, a fidelity is
                specified for each coupling.
            one_qubit_gate_depolarization_rates (Dict[str, Dict[int, float]]): for each one-qubit gate, a depolarization
                rate is specified for each qubit.
            two_qubit_gate_depolarization_rates (Dict[str, Dict[Tuple[int], float]]): for each two-qubit gate, a
                depolarization rate is specified for each coupling.
            one_qubit_gate_durations (Dict[str, float]): for each one-qubit gate, a duration is specified.
            two_qubit_gate_durations (Dict[str, float]): for each two-qubit gate, a duration is specified.
            id_ (Union[str, None], optional): the identifier of the chip sample. Defaults to None.

        Example:
            IQMChipSample(quantum_architecture=ThreeQubitExample(),
                          t1s=[10000., 12000., 14000.],
                          t2s=[10000., 12000., 13000.],
                          one_qubit_gate_fidelities={"r": {0: 0.999,
                                                           1: 0.996,
                                                           2: 0.998}},
                          two_qubit_gate_fidelities={"cz": {(0, 1): 0.995,
                                                            (1, 2): 0.997}},
                          one_qubit_gate_depolarization_rates={"r": {0: 0.0005,
                                                                     1: 0.0004,
                                                                     2: 0.0010}},
                          two_qubit_gate_depolarization_rates={"cz": {(0, 1): 0.08,
                                                                      (1, 2): 0.03}},
                          one_qubit_gate_durations={"r": 50.},
                          two_qubit_gate_durations={"cz": 100.},
                          id_="threequbit-example_sample")
        """
        self.quantum_architecture = quantum_architecture
        self.no_qubits = len(t1s)
        self.t1s = t1s
        self.t2s = t2s
        self.one_qubit_gate_fidelities = one_qubit_gate_fidelities
        self.two_qubit_gate_fidelities = two_qubit_gate_fidelities
        self.gate_fidelities = self.one_qubit_gate_fidelities | self.two_qubit_gate_fidelities
        self.one_qubit_gate_depolarization_rates = one_qubit_gate_depolarization_rates
        self.two_qubit_gate_depolarization_rates = two_qubit_gate_depolarization_rates
        self.gate_depolarization_rates = (
            self.one_qubit_gate_depolarization_rates | self.two_qubit_gate_depolarization_rates
        )
        self.one_qubit_gate_durations = one_qubit_gate_durations
        self.two_qubit_gate_durations = two_qubit_gate_durations
        self.gate_durations = self.one_qubit_gate_durations | self.two_qubit_gate_durations
        self.id_ = id_

        self._validate_parameters()

    def _validate_parameters(self):
        """Verifies that the parameters of the chip sample match the constraints of its IQMQuantumArchitecture.

        Raises:
            ValueError: Length of `t1s` and number of qubits should match.
            ValueError: Length of `t2s` and number of qubits should match.
            ValueError: Length of `one_qubit_gate` parameter lists and number of qubits should match.
            ValueError: Length of `two_qubit_gate` parameter lists and number of couplings should match.
            ValueError: Gates in gate parameter lists must be supported by the quantum architecture.

        Returns:
            bool: True if parameters are correctly verified.
        """
        # Check that T1 list has one element for each qubit
        if len(self.t1s) != self.quantum_architecture.no_qubits:
            raise ValueError(
                f"Length of `t1s` ({len(self.t1s)}) and number of qubits ({self.quantum_architecture.no_qubits}) should match."
            )

        # Check that T2 list has one element for each qubit
        if len(self.t2s) != self.quantum_architecture.no_qubits:
            raise ValueError(
                f"Length of `t2s` ({len(self.t2s)}) and number of qubits ({self.quantum_architecture.no_qubits}) should match."
            )

        # Check that one-qubit gate parameter qubits match those of the architecture
        for property_name, property_dict in [
            ("fidelities", self.one_qubit_gate_fidelities),
            ("depolarization rates", self.one_qubit_gate_depolarization_rates),
        ]:
            for gate, gate_dict in property_dict.items():
                if set(gate_dict.keys()) != set(range(self.quantum_architecture.no_qubits)):
                    raise ValueError(
                        f"The qubits specified for one-qubit gate {property_name} ({set(gate_dict.keys())}) don't match the qubits of the quantum architecture `{self.quantum_architecture.id_}` ({set(range(self.quantum_architecture.no_qubits))})."
                    )

        # Check that two-qubit gate parameter couplings match those of the architecture
        for property_name, property_dict in [
            ("fidelities", self.two_qubit_gate_fidelities),
            ("depolarization rates", self.two_qubit_gate_depolarization_rates),
        ]:
            for gate, gate_dict in property_dict.items():
                if set(gate_dict.keys()) != set(self.quantum_architecture.topology):
                    raise ValueError(
                        f"The couplings specified for two-qubit gate {property_name} ({set(gate_dict.keys())}) don't match the couplings of the quantum architecture `{self.quantum_architecture.id_}` ({set(self.quantum_architecture.topology)})."
                    )

        # Check that the basis gates of the chip sample match the quantum architecture's
        for property_name, property_dict in [
            ("fidelities", self.gate_fidelities),
            ("depolarization_rates", self.gate_depolarization_rates),
            ("durations", self.gate_durations),
        ]:
            for gate in property_dict.keys():
                if gate not in self.quantum_architecture.basis_gates:
                    raise ValueError(
                        f"Gate `{gate}` in `gate_{property_name}` is not supported by quantum architecture `{self.quantum_architecture.id_}`. Valid gates: {self.quantum_architecture.basis_gates}"
                    )

        return True
