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
from typing import Optional

from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers.builtin_plugins import PassManagerStagePlugin

from iqm.iqm_client.transpile import ExistingMoveHandlingOptions
from iqm.qiskit_iqm.iqm_backend import IQMTarget
from iqm.qiskit_iqm.iqm_naive_move_pass import IQMNaiveResonatorMoving
from iqm.qiskit_iqm.iqm_transpilation import IQMOptimizeSingleQubitGates


class IQMSchedulingPlugin(PassManagerStagePlugin):
    """Basic plugin for scheduling stage of IQM devices.

    Args:
        move_gate_routing: whether to include MoveGate routing in the scheduling stage.
        optimize_sqg: Whether to include single qubit gate optimization in the scheduling stage.
        drop_final_rz: Whether to drop trailing RZ gates in the circuit during single qubit gate optimization.
        ignore_barriers: Whether to ignore barriers during single qubit gate optimization.
        existing_move_handling: How to handle existing MoveGates in the circuit during MoveGate routing.
    Raises:
        ValueError: When incompatible options are set.
    """

    def __init__(
        self,
        move_gate_routing: bool,
        optimize_sqg: bool,
        drop_final_rz: bool,
        ignore_barriers: bool,
        existing_move_handling: Optional[ExistingMoveHandlingOptions],
    ) -> None:
        # pylint: disable=too-many-arguments
        super().__init__()
        self.move_gate_routing = move_gate_routing
        self.optimize_sqg = optimize_sqg
        self.drop_final_rz = drop_final_rz
        self.ignore_barriers = ignore_barriers
        self.existing_move_handling = (
            existing_move_handling if existing_move_handling is not None else ExistingMoveHandlingOptions.KEEP
        )

    def pass_manager(
        self, pass_manager_config: PassManagerConfig, optimization_level: Optional[int] = None
    ) -> PassManager:
        """Build scheduling stage PassManager"""

        scheduling = PassManager()
        if self.optimize_sqg:
            scheduling.append(
                IQMOptimizeSingleQubitGates(drop_final_rz=self.drop_final_rz, ignore_barriers=self.ignore_barriers)
            )
        if pass_manager_config.target is None:
            raise ValueError("PassManagerConfig must have a target backend set, unable to schedule MoveGate routing.")
        if self.move_gate_routing and isinstance(pass_manager_config.target, IQMTarget):
            scheduling.append(
                IQMNaiveResonatorMoving(
                    target=pass_manager_config.target,
                    existing_moves_handling=self.existing_move_handling,
                )
            )
        return scheduling


class MoveGateRoutingPlugin(IQMSchedulingPlugin):
    """Plugin class for IQM single qubit gate optimization and MoveGate routing as a scheduling stage."""

    def __init__(
        self,
        optimize_sqg: bool = True,
        drop_final_rz: bool = True,
        ignore_barriers: bool = False,
        existing_move_handling: Optional[ExistingMoveHandlingOptions] = None,
    ) -> None:
        super().__init__(True, optimize_sqg, drop_final_rz, ignore_barriers, existing_move_handling)


class MoveGateRoutingOnlyPlugin(MoveGateRoutingPlugin):
    """Plugin class for MoveGate routing without single qubit gate optimization as a scheduling stage."""

    def __init__(self):
        super().__init__(optimize_sqg=False)


class MoveGateRoutingKeepExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for single qubit gate optimization and MoveGate routing where existing moves are kept."""

    def __init__(self):
        super().__init__(
            optimize_sqg=True,
            existing_move_handling=ExistingMoveHandlingOptions.KEEP,
        )


class MoveGateRoutingRemoveExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for single qubit gate optimization and MoveGate routing where existing moves are removed."""

    def __init__(self):
        super().__init__(
            optimize_sqg=True,
            existing_move_handling=ExistingMoveHandlingOptions.REMOVE,
        )


class MoveGateRoutingTrustExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for single qubit gate optimization and MoveGate routing where existing moves are not checked."""

    def __init__(self):
        super().__init__(
            optimize_sqg=True,
            existing_move_handling=ExistingMoveHandlingOptions.TRUST,
        )


class MoveGateRoutingWithExactRZPlugin(MoveGateRoutingPlugin):
    """Plugin class for single qubit gate optimization and MoveGate routing where
    trailing RZ gates are kept in the circuit.
    """

    def __init__(self):
        super().__init__(optimize_sqg=True, drop_final_rz=False)


class MoveGateRoutingWithRZOptimizationIgnoreBarriersPlugin(MoveGateRoutingPlugin):
    """Plugin class for single qubit gate optimization and MoveGate routing where barriers are ignored during
    optimization.
    """

    def __init__(self):
        super().__init__(
            optimize_sqg=True,
            ignore_barriers=True,
        )


class MoveGateRoutingOnlyKeepExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for MoveGate routing without single qubit gate optimization
    where existing moves are kept."""

    def __init__(self):
        super().__init__(
            optimize_sqg=False,
            existing_move_handling=ExistingMoveHandlingOptions.KEEP,
        )


class MoveGateRoutingOnlyRemoveExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for MoveGate routing without single qubit gate optimization
    where existing moves are removed."""

    def __init__(self):
        super().__init__(
            optimize_sqg=False,
            existing_move_handling=ExistingMoveHandlingOptions.REMOVE,
        )


class MoveGateRoutingOnlyTrustExistingMovesPlugin(MoveGateRoutingPlugin):
    """Plugin class for MoveGate routing without single qubit gate optimization
    where existing moves are not checked."""

    def __init__(self):
        super().__init__(
            optimize_sqg=False,
            existing_move_handling=ExistingMoveHandlingOptions.TRUST,
        )


class OnlyRZOptimizationPlugin(IQMSchedulingPlugin):
    """Plugin class for single qubit gate optimization without MOVE gate routing."""

    def __init__(
        self,
        drop_final_rz=True,
        ignore_barriers=False,
    ):
        super().__init__(False, True, drop_final_rz, ignore_barriers, None)


class OnlyRZOptimizationExactPlugin(OnlyRZOptimizationPlugin):
    """Plugin class for single qubit gate optimization without MOVE gate routing and
    the final RZ gates are not dropped.
    """

    def __init__(self):
        super().__init__(drop_final_rz=False)


class OnlyRZOptimizationIgnoreBarriersPlugin(OnlyRZOptimizationPlugin):
    """Plugin class for single qubit gate optimization without MOVE gate routing where barriers are ignored."""

    def __init__(self):
        super().__init__(ignore_barriers=True)


class OnlyRZOptimizationExactIgnoreBarriersPlugin(OnlyRZOptimizationPlugin):
    """Plugin class for single qubit gate optimization without MOVE gate routing and
    the final RZ gates are not dropped.
    """

    def __init__(self):
        super().__init__(drop_final_rz=False, ignore_barriers=True)


class IQMDefaultSchedulingPlugin(IQMSchedulingPlugin):
    """Plugin class for IQM single qubit gate optimization and MoveGate routing as a scheduling stage."""

    def __init__(self) -> None:
        super().__init__(
            True, optimize_sqg=True, drop_final_rz=True, ignore_barriers=False, existing_move_handling=None
        )

    def pass_manager(
        self, pass_manager_config: PassManagerConfig, optimization_level: Optional[int] = None
    ) -> PassManager:
        """Build scheduling stage PassManager"""
        if optimization_level == 0:
            self.optimize_sqg = False
        return super().pass_manager(pass_manager_config, optimization_level)
