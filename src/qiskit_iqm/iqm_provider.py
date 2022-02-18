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
from iqm_client.iqm_client import IQMClient
import json

from qiskit_iqm.iqm_backend import IQMBackend


class IQMProvider:
    """Provider for IQM backend.

    Args:
        url:
        settings_path:
        username:
        api_key:
    """
    def __init__(self, url: str, settings_path: str, username: str = None, api_key: str = None):
        with open(settings_path, 'r') as f:
            self._client = IQMClient(url, json.loads(f.read()), username, api_key)

    def backends(self, *args, **kwargs):
        raise NotImplementedError('IQM server hosts one backend only which can be retrieved by the get_backend method')

    def get_backend(self):
        return IQMBackend(self._client)
