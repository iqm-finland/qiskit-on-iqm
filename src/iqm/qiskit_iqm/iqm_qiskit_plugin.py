# Copyright 2024 Qiskit on IQM developers
"""Transpiler plugins for IQM N-star architecture"""

from typing import Optional

from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin

from iqm.qiskit_iqm.iqm_naive_move_pass import build_IQM_star_pass


class TranslateIQMPlugin(PassManagerStagePlugin):
    """Translate to n-star architecture"""

    def pass_manager(
        self, pass_manager_config: PassManagerConfig, optimization_level: Optional[int] = None
    ) -> PassManager:
        return PassManager(build_IQM_star_pass(pass_manager_config))
