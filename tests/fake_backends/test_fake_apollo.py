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

from iqm.qiskit_iqm import IQMFakeApollo


def test_iqm_fake_adonis():
    backend = IQMFakeApollo()
    assert backend.num_qubits == 20


def test_iqm_fake_adonis_connectivity():
    backend = IQMFakeApollo()
    assert backend.coupling_map.get_edges() == [
        (0, 1),
        (0, 3),
        (1, 4),
        (2, 3),
        (7, 2),
        (3, 4),
        (8, 3),
        (4, 5),
        (9, 4),
        (5, 6),
        (10, 5),
        (11, 6),
        (7, 8),
        (7, 12),
        (8, 9),
        (8, 13),
        (9, 10),
        (9, 14),
        (10, 11),
        (15, 10),
        (16, 11),
        (12, 13),
        (13, 14),
        (17, 13),
        (15, 14),
        (18, 14),
        (15, 16),
        (15, 19),
        (17, 18),
        (18, 19),
    ]


def test_iqm_fake_adonis_noise_model_instantiated():
    backend = IQMFakeApollo()
    assert isinstance(backend.noise_model, NoiseModel)
