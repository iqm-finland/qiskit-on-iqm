# Copyright 2024 Qiskit on IQM developers
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
"""Collection of Qiskit transpiler plugins for native use of specialized transpiler passes by our devices."""

from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.preset_passmanagers.builtin_plugins import PassManagerStagePlugin

from iqm.qiskit_iqm.iqm_backend import IQMStarTarget
from iqm.qiskit_iqm.iqm_naive_move_pass import IQMNaiveResonatorMoving
from iqm.qiskit_iqm.iqm_transpilation import IQMOptimizeSingleQubitGates


class MoveGateRoutingPlugin(PassManagerStagePlugin):
    """Plugin class for IQM single qubit gate optimization and MoveGate routing as a scheduling stage."""

    def pass_manager(self, pass_manager_config, optimization_level=None) -> PassManager:
        """Build scheduling stage PassManager"""

        scheduling = PassManager()
        scheduling.append(IQMOptimizeSingleQubitGates(drop_final_rz=True, ignore_barriers=False))
        # TODO Update the IQMNaiveResonatorMoving to use the IQMStarTarget and the transpiler_insert_moves function
        if isinstance(pass_manager_config.target, IQMStarTarget):
            scheduling.append(
                IQMNaiveResonatorMoving(target=pass_manager_config.target, gate_set=pass_manager_config.basis_gates)
            )
        return scheduling
