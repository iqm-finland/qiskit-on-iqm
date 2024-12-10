# Copyright 2024 Qiskit on IQM developers
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
"""This file is an example of using Qiskit on IQM to run a simple but non-trivial quantum circuit on
Resonance, the IQM quantum cloud service.
See the Qiskit on IQM user guide for instructions:
https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html
"""

import argparse
from typing import Optional

from qiskit import QuantumCircuit

from iqm.qiskit_iqm import IQMProvider, transpile_to_IQM


def resonance_example(server_url: str, api_token: Optional[str]) -> dict[str, int]:
    """Run a circuit via IQM Resonance.

    Args:
        server_url: URL of the IQM Resonance QC used for execution
        api_token: IQM Resonance API token for authentication

    Returns:
        a mapping of bitstrings representing qubit measurement results to counts for each result
    """
    SHOTS = 1000

    # Define a quantum circuit
    num_qb = 5
    qc = QuantumCircuit(num_qb)

    qc.h(0)
    for qb in range(1, num_qb):
        qc.cx(0, qb)
    qc.barrier()
    qc.measure_all()

    # Initialize a backend
    backend = IQMProvider(server_url, token=api_token).get_backend()

    # Transpile the circuit
    qc_transpiled = transpile_to_IQM(qc, backend)
    print(qc_transpiled.draw(output='text'))

    # Run the circuit
    job = backend.run(qc_transpiled, shots=SHOTS)
    return job.result().get_counts()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '--url',
        help='URL of the IQM Resonance QC',
        # For example https://cocos.resonance.meetiqm.com/garnet
        default='https://cocos.resonance.meetiqm.com/<QUANTUM COMPUTER>',
    )
    argparser.add_argument(
        '--token',
        help='IQM Resonance access token',
        # Provide the API token explicitly or set it as an environment variable
        # following the https://iqm-finland.github.io/qiskit-on-iqm/user_guide.html#authentication
        default='<INSERT YOUR TOKEN>',
    )

    args = argparser.parse_args()
    results = resonance_example(args.url, args.token)
    print(results)
