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
"""Types for representing and methods for manipulating operations on IQM's quantum computers.
"""
from importlib.metadata import PackageNotFoundError, version

from qiskit_iqm.iqm_backend import IQMBackend
from qiskit_iqm.iqm_job import IQMJob
from qiskit_iqm.iqm_provider import IQMProvider

try:
    dist_name = "qiskit-iqm"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError
