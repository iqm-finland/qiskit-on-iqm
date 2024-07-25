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

"""Testing fake Deneb backend.
"""
from qiskit_aer.noise.noise_model import NoiseModel

from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb


def test_iqm_fake_deneb():
    backend = IQMFakeDeneb()
    assert backend.num_qubits == 7
    assert backend.name == 'IQMFakeDenebBackend'


def test_iqm_fake_deneb_connectivity(deneb_coupling_map):
    backend = IQMFakeDeneb()
    assert set(backend.coupling_map.get_edges()) == deneb_coupling_map


def test_iqm_fake_deneb_noise_model_instantiated():
    backend = IQMFakeDeneb()
    assert isinstance(backend.noise_model, NoiseModel)
