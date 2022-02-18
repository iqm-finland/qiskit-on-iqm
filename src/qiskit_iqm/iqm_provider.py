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

"""
Provider for IQM backend.
"""
import json

from iqm_client.iqm_client import IQMClient

from qiskit_iqm.iqm_backend import IQMBackend


class IQMProvider:
    """Provider for IQM backend.

    Args:
        url: URL of the IQM server.
        settings_path: Path to the JSON settings file for the IQM backend.
        username: Username, if required by the IQM Cortex server. This can also be set in the IQM_SERVER_USERNAME
                  environment variable.
        api_key: API key, if required by the IQM Cortex server. This can also be set in the IQM_SERVER_API_KEY
                 environment variable.
    """
    def __init__(self, url: str, settings_path: str, username: str = None, api_key: str = None):
        with open(settings_path, 'r', encoding='utf-8') as f:
            self._client = IQMClient(url, json.loads(f.read()), username, api_key)

    def get_backend(self) -> IQMBackend:
        """Get IQMBackend instance associated with this provider"""
        return IQMBackend(self._client)
