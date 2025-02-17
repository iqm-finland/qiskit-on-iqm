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

"""Testing fake Aphrodite backend.
"""
from qiskit_aer.noise.noise_model import NoiseModel

from iqm.qiskit_iqm.fake_backends.fake_aphrodite import IQMFakeAphrodite
from iqm.qiskit_iqm.iqm_backend import IQMTarget


def test_iqm_fake_aphrodite():
    backend = IQMFakeAphrodite()
    assert backend.num_qubits == 54
    assert backend.name == 'IQMFakeAphroditeBackend'


def test_iqm_fake_aphrodite_connectivity():
    backend = IQMFakeAphrodite()
    coupling_map = {
        (0, 1),
        (0, 4),
        (1, 5),
        (2, 3),
        (2, 8),
        (3, 4),
        (3, 9),
        (4, 5),
        (4, 10),
        (5, 6),
        (5, 11),
        (6, 12),
        (7, 8),
        (7, 15),
        (8, 9),
        (8, 16),
        (9, 10),
        (9, 17),
        (10, 11),
        (10, 18),
        (11, 12),
        (11, 19),
        (12, 13),
        (12, 20),
        (13, 21),
        (14, 15),
        (14, 22),
        (15, 16),
        (15, 23),
        (16, 17),
        (16, 24),
        (17, 18),
        (17, 25),
        (18, 19),
        (18, 26),
        (19, 20),
        (19, 27),
        (20, 21),
        (20, 28),
        (21, 29),
        (22, 23),
        (23, 24),
        (23, 31),
        (24, 25),
        (24, 32),
        (25, 26),
        (25, 33),
        (26, 27),
        (26, 34),
        (27, 28),
        (27, 35),
        (28, 29),
        (28, 36),
        (29, 30),
        (29, 37),
        (30, 38),
        (31, 32),
        (31, 39),
        (32, 33),
        (32, 40),
        (33, 34),
        (33, 41),
        (34, 35),
        (34, 42),
        (35, 36),
        (35, 43),
        (36, 37),
        (36, 44),
        (37, 38),
        (37, 45),
        (39, 40),
        (40, 41),
        (40, 46),
        (41, 42),
        (41, 47),
        (42, 43),
        (42, 48),
        (43, 44),
        (43, 49),
        (44, 45),
        (44, 50),
        (46, 47),
        (47, 48),
        (47, 51),
        (48, 49),
        (48, 52),
        (49, 50),
        (49, 53),
        (51, 52),
        (52, 53),
    }
    assert isinstance(backend.target, IQMTarget)
    assert set(backend.target.build_coupling_map()) == coupling_map
    assert set(backend.coupling_map.get_edges()) == coupling_map
    assert backend.target_with_resonators == backend.target


def test_iqm_fake_aphrodite_noise_model_instantiated():
    backend = IQMFakeAphrodite()
    assert isinstance(backend.noise_model, NoiseModel)
