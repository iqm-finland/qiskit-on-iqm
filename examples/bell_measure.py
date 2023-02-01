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
computer.
1. Download this file
2. Install Qiskit on IQM as instructed in the user guide:
  https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html#installation
3. Install Cortex CLI and log in as instructed here:
  https://iqm-finland.github.io/cortex-cli/readme.html#installing-cortex-cli
4. Set the environment variable as instructed by Cortex CLI after logging in
5. Run `python bell_measure.py --server_url https://demo.qc.iqm.fi/cocos` – replace the example URL with the correct URL
6. The output should show that almost half of the measurements resulted in '00' and almost half in '11'
"""

import argparse
from qiskit import execute, QuantumCircuit
from qiskit_iqm import IQMProvider

argparser = argparse.ArgumentParser()
argparser.add_argument('--server_url', help='URL of the IQM server', default='https://demo.qc.iqm.fi/cocos')
server_url = argparser.parse_args().server_url

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

print(execute(circuit, IQMProvider(server_url).get_backend(), shots=1000).result().get_counts())
