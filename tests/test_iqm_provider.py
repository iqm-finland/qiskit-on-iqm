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
from qiskit_iqm import IQMBackend, IQMProvider


def test_get_backend(tmp_path):
    settings_file = tmp_path / 'a_file'
    settings_file.write_text('{}')
    provider = IQMProvider('http://some_url', str(settings_file))
    backend = provider.get_backend()
    assert isinstance(backend, IQMBackend)
