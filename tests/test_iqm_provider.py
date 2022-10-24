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

"""Testing IQM provider.
"""
from iqm_client import IQMClient
from mockito import when

from qiskit_iqm import IQMBackend, IQMProvider


def test_get_backend(linear_architecture_3q):
    url = 'http://some_url'
    when(IQMClient).get_quantum_architecture().thenReturn(linear_architecture_3q)

    provider = IQMProvider(url)
    backend = provider.get_backend()

    assert isinstance(backend, IQMBackend)
    assert backend.client._base_url == url
    assert backend.num_qubits == 3
    assert set(backend.coupling_map.get_edges()) == {(0, 1), (1, 2)}
