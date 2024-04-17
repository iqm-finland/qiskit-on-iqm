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

from iqm.qiskit_iqm.iqm_provider import IQMProvider


def bell_measure(server_url: str) -> dict[str, int]:
    """Execute a circuit that prepares and measures a Bell state.

    Args:
        server_url: URL of the IQM Cortex server used for execution

    Returns:
        a mapping of bitstrings representing qubit measurement results to counts for each result
    """
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return execute(circuit, IQMProvider(server_url).get_backend(), shots=1000).result().get_counts()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '--cortex_server_url',
        help='URL of the IQM Cortex server',
        default='https://demo.qc.iqm.fi/cocos',
    )
    print(bell_measure(argparser.parse_args().cortex_server_url))
