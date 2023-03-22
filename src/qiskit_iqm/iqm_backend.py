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
"""Qiskit backend for IQM quantum computers.
"""
from __future__ import annotations

from abc import ABC
import re
from typing import Final, Optional

from iqm_client import QuantumArchitectureSpecification
from qiskit.circuit import Parameter
from qiskit.circuit.library import CZGate, Measure, RGate
from qiskit.providers import BackendV2
from qiskit.transpiler import Target

IQM_TO_QISKIT_GATE_NAME: Final[dict[str, str]] = {'phased_rx': 'r', 'cz': 'cz'}


class IQMBackendBase(BackendV2, ABC):
    """Abstract base class for various IQM-specific backends.

    Args:
        architecture: Description of the quantum architecture associated with the backend instance.
    """

    def __init__(self, architecture: QuantumArchitectureSpecification, **kwargs):
        super().__init__(**kwargs)

        def get_num_or_zero(name: str) -> int:
            match = re.search(r'(\d+)', name)
            return int(match.group(1)) if match else 0

        qb_to_idx = {qb: idx for idx, qb in enumerate(sorted(architecture.qubits, key=get_num_or_zero))}

        target = Target()
        # There is no dedicated direct way of setting just the qubit connectivity and the native gates to the target.
        # Such info is automatically deduced once all instruction properties are set. Currently, we do not retrieve
        # any properties from the server, and we are interested only in letting the target know what is the native gate
        # set and the connectivity of the device under use. Thus, we populate the target with None properties.
        target.add_instruction(
            RGate(Parameter('theta'), Parameter('phi')), {(qb_to_idx[qb],): None for qb in architecture.qubits}
        )
        target.add_instruction(
            CZGate(), {(qb_to_idx[qb1], qb_to_idx[qb2]): None for qb1, qb2 in architecture.qubit_connectivity}
        )
        target.add_instruction(Measure(), {(qb_to_idx[qb],): None for qb in architecture.qubits})

        self._target = target
        self._qb_to_idx = qb_to_idx
        self._idx_to_qb = {v: k for k, v in qb_to_idx.items()}

    @property
    def target(self) -> Target:
        return self._target

    def qubit_name_to_index(self, name: str) -> Optional[int]:
        """Given an IQM-style qubit name ('QB1', 'QB2', etc.) return the corresponding index in the register. Returns
        None is the given name does not belong to the backend."""
        return self._qb_to_idx.get(name)

    def index_to_qubit_name(self, index: int) -> Optional[str]:
        """Given an index in the backend register return the corresponding IQM-style qubit name ('QB1', 'QB2', etc.).
        Returns None if the given index does not correspond to any qubit in the backend."""
        return self._idx_to_qb.get(index)
