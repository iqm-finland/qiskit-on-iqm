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

"""Testing fake Adonis backend.
"""
from qiskit_aer.noise.noise_model import NoiseModel

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.iqm_backend import IQMTarget


def test_iqm_fake_adonis():
    backend = IQMFakeAdonis()
    assert backend.num_qubits == 5
    assert backend.name == 'IQMFakeAdonisBackend'


def test_iqm_fake_adonis_connectivity():
    backend = IQMFakeAdonis()
    coupling_map = {(0, 2), (1, 2), (3, 2), (4, 2)}
    assert isinstance(backend.target, IQMTarget)
    assert set(backend.target.build_coupling_map()) == coupling_map
    assert set(backend.coupling_map.get_edges()) == coupling_map
    assert backend.target_with_resonators == backend.target


def test_iqm_fake_adonis_noise_model_instantiated():
    backend = IQMFakeAdonis()
    assert isinstance(backend.noise_model, NoiseModel)
