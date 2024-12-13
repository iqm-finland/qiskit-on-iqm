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

"""Testing fake Apollo backend.
"""
from qiskit_aer.noise.noise_model import NoiseModel

from iqm.qiskit_iqm import IQMFakeApollo


def connectivity_to_coupling_map(connectivity: list[list[str]]) -> set[tuple[int, int]]:
    """Convert IQMFakeBackend qubit names "QB{i}" to Qiskit indices."""
    return {tuple(int(q[2:]) - 1 for q in pair) for pair in connectivity}


def test_iqm_fake_apollo():
    backend = IQMFakeApollo()
    assert backend.num_qubits == 20
    assert backend.name == 'IQMFakeApolloBackend'


def test_iqm_fake_apollo_connectivity():
    backend = IQMFakeApollo()
    # for current fake backends, cz connectivity is the same as the QPU connectivity
    apollo_coupling_map = connectivity_to_coupling_map(backend.architecture.gates['cz'].loci)
    assert set(backend.coupling_map.get_edges()) == apollo_coupling_map


def test_iqm_fake_apollo_noise_model_instantiated():
    backend = IQMFakeApollo()
    assert isinstance(backend.noise_model, NoiseModel)
