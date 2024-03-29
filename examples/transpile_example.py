# Copyright 2023 Qiskit on IQM developers
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
"""This file is an example of using Qiskit on IQM to execute a simple but non-trivial quantum circuit on an IQM quantum
computer. See the Qiskit on IQM user guide for instructions:
https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html
"""

import argparse

from qiskit import QuantumCircuit, execute

from iqm.qiskit_iqm import transpile_to_IQM
from iqm.qiskit_iqm.iqm_provider import IQMProvider

argparser = argparse.ArgumentParser()
argparser.add_argument(
    '--url',
    help='URL of the IQM service',
    default='https://cocos.resonance.meetiqm.com/deneb',
)
server_url = argparser.parse_args().url

circuit = QuantumCircuit(5)
circuit.h(0)
for i in range(1, 5):
    circuit.cx(0, i)
circuit.measure_all()

backend = IQMProvider(server_url).get_backend()
transpiled_circuit = transpile_to_IQM(circuit, backend)

print(transpiled_circuit)
print(execute(transpiled_circuit, backend, shots=1000).result().get_counts())
