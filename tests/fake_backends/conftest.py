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
"""Shared utilities for fake backend tests.
"""

import pytest

from iqm.qiskit_iqm.fake_backends import IQMErrorProfile


@pytest.fixture
def create_3q_error_profile():
    """Create a ChipSample instance with some default properties, unless overriden by kwargs"""

    def error_profile(**kwargs):
        error_profile_contents = {
            "t1s": {"QB1": 2000, "QB2": 2000, "QB3": 2000},
            "t2s": {"QB1": 1000, "QB2": 1000, "QB3": 1000},
            "single_qubit_gate_depolarizing_error_parameters": {"prx": {"QB1": 0.0001, "QB2": 0.0001, "QB3": 0}},
            "two_qubit_gate_depolarizing_error_parameters": {"cz": {("QB1", "QB2"): 0.001, ("QB2", "QB3"): 0.001}},
            "single_qubit_gate_durations": {"prx": 1.0},
            "two_qubit_gate_durations": {"cz": 1.5},
            "readout_errors": {
                "QB1": {"0": 0.02, "1": 0.03},
                "QB2": {"0": 0.02, "1": 0.03},
                "QB3": {"0": 0.02, "1": 0.03},
            },
            "name": "adonis-example_sample",
        }
        error_profile_contents.update(kwargs)
        return IQMErrorProfile(**error_profile_contents)

    return error_profile
