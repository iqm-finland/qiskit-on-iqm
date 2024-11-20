# Copyright 2023 Qiskit on IQM developers
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

"""Testing Resonance example script.
"""


import subprocess
import sys

from iqm.qiskit_iqm.examples import resonance_example


def test_resonance_example_call():
    """Test that example script runs and fails at establishing a connection."""
    with subprocess.Popen(
        (sys.executable, resonance_example.__file__, "--url", "https://not.a.real.domain", "--token", "fake_token"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as p:
        (_, err) = p.communicate()
        p.wait()
        assert "ConnectionError" in str(err)
