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

"""Testing IQM Chip sample.
"""
import pytest


def test_chip_sample_with_incomplete_t1s(create_chip_sample):
    """Test that ChipSample construction fails if T1 times are not provided for all qubits"""
    with pytest.raises(ValueError, match="Length of t1s"):
        create_chip_sample(t1s={'QB1': 2000, 'QB3': 2000})


# TODO: test all other validations as well
