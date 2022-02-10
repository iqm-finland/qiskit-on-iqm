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
import warnings
from typing import Iterable, Union, List

from iqm_client import iqm_client
from qiskit import QuantumCircuit
from qiskit.providers import BackendV2 as Backend, QubitProperties, Options
from qiskit.transpiler import Target

from qiskit_iqm_provider.iqm_job import IQMJob
from qiskit_iqm_provider.iqm_instruction_mapping import map_instruction


def serialize_circuit(circuit: QuantumCircuit) -> iqm_client.Circuit:
    """Serializes a quantum circuit into the IQM data transfer format.

    Args:
        circuit: quantum circuit to serialize

    Returns:
        data transfer object representing the circuit
    """
    instructions = list(map(lambda x: map_instruction(x[0], x[1], x[2]), circuit))
    return iqm_client.Circuit(
        name='Serialized from Qiskit',
        instructions=instructions
    )


class IQMBackend(Backend):
    @property
    def target(self) -> Target:
        raise NotImplementedError

    @property
    def max_circuits(self):
        raise NotImplementedError

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=1)

    @property
    def dtm(self) -> float:
        raise NotImplementedError

    @property
    def meas_map(self) -> List[List[int]]:
        raise NotImplementedError

    def qubit_properties(self, qubit: Union[int, List[int]]) -> Union[QubitProperties, List[QubitProperties]]:
        raise NotImplementedError

    def drive_channel(self, qubit: int):
        raise NotImplementedError

    def measure_channel(self, qubit: int):
        raise NotImplementedError

    def acquire_channel(self, qubit: int):
        raise NotImplementedError

    def control_channel(self, qubits: Iterable[int]):
        raise NotImplementedError

    def run(self, circuit, **kwargs):
        for option in kwargs:
            if not hasattr(option, self.options):
                warnings.warn(
                    "Option %s is not used by the IQM backend" % option,
                    UserWarning, stacklevel=2)
        job_json = serialize_circuit(circuit)
        job_handle = self._submit(job_json)
        return IQMJob(backend=self, job_id=job_handle)

    def _submit(self, iqm_json):
        raise NotImplementedError
