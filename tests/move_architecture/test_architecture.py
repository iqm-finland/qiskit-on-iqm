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
"""Testing extended quantum architecture specification.
"""
import pytest

from tests.utils import get_mocked_backend


@pytest.fixture
def dqa(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    "dqa",
    [
        "move_architecture",
        "adonis_architecture",
        "hypothetical_fake_architecture",
        "ndonis_architecture",
        "linear_3q_architecture",
    ],
    indirect=True,
)
class TestIQMTargetReflectsDQA:
    """Test that the IQM backend reflects the extended architecture."""

    @pytest.fixture(autouse=True)
    def init_backend(self, dqa):
        """Initialize the backend with the given architecture."""
        # pylint: disable=attribute-defined-outside-init
        self.dqa = dqa
        self.backend = get_mocked_backend(dqa)[0]

    def test_physical_qubits(self):
        """Check that the physical qubits are in the correct order: resonators at the end."""
        assert self.backend.physical_qubits == self.dqa.qubits + self.dqa.computational_resonators

    def test_target_gate_set(self):
        """Check that gate set of the target is the same as we support according to the DQA."""
        IQM_TO_QISKIT = {
            "prx": "r",
            "cc_prx": "reset",
            "cz": "cz",
            "move": "cz",
            "measure": "measure",
        }
        assert set(self.backend.target.operation_names) == set(
            [IQM_TO_QISKIT[name] for name in self.dqa.gates] + ["id"]
        )
        if self.backend._fake_target_with_moves is not None:
            IQM_TO_QISKIT["move"] = "move"
            assert set(self.backend._fake_target_with_moves.operation_names) == set(
                [IQM_TO_QISKIT[name] for name in self.dqa.gates] + ["id"]
            )

    @pytest.mark.parametrize(("qiskit_name", "iqm_name"), zip(["r", "measure", "reset"], ["prx", "measure", "cc_prx"]))
    def test_1_to_1_corresponding_gates(self, qiskit_name, iqm_name):
        """Check that the gates are defined for the correct qubits where the gates correspond 1-1 directly."""
        self.check_instruction(
            qiskit_name,
            iqm_name=iqm_name,
        )
        if self.backend._fake_target_with_moves is not None:
            self.check_instruction(qiskit_name, iqm_name=iqm_name, target=self.backend._fake_target_with_moves)

    def test_id_gates(self):
        """Check that the id gates are defined for both qubits and components."""
        self.check_instruction("id", expected_loci=[(q,) for q in self.dqa.components])
        if self.backend._fake_target_with_moves is not None:
            self.check_instruction(
                "id", expected_loci=[(q,) for q in self.dqa.components], target=self.backend._fake_target_with_moves
            )

    def test_cz_gates(self):
        """Check that the cz gates are defined for the correct qubits."""
        if "move" not in self.dqa.gates:
            self.check_instruction("cz", iqm_name="cz")
        else:
            self.validate_move_loci()
            self.validate_fake_cz_loci()

    def validate_move_loci(self):
        """Confirms that the move gate is not in the target."""
        assert "move" not in self.backend.target.operation_names

    def validate_fake_cz_loci(self):
        """Check that the virtual czs in the target are as expected."""
        target_loci = [
            tuple(self.backend.index_to_qubit_name(qb) for qb in loci)
            for i, loci in self.backend._fake_target_with_moves.instructions
            if i.name == "cz"
        ]
        real_cz_loci = list(
            self.dqa.gates["cz"].implementations[self.dqa.gates["cz"].default_implementation].loci,
        )
        real_move_loci = list(
            self.dqa.gates["move"].implementations[self.dqa.gates["move"].default_implementation].loci,
        )
        for loci in target_loci:
            if loci not in real_cz_loci:
                sandwich_found = False
                for move_qb, res in real_move_loci:
                    if move_qb == loci[0] and ((loci[1], res) in real_cz_loci or (res, loci[1]) in real_cz_loci):
                        sandwich_found = True
                        break
                    if move_qb == loci[1] and ((loci[0], res) in real_cz_loci or (res, loci[0]) in real_cz_loci):
                        sandwich_found = True
                        break
                assert sandwich_found

    def test_fake_target_with_moves(self):
        """Check that the fake target is correctly generated."""
        if "move" in self.dqa.gates:
            self.validate_move_loci_fake_target()
            self.validate_cz_loci_fake_target()
        else:
            assert self.backend._fake_target_with_moves is None

    def validate_move_loci_fake_target(self):
        """Check that the moves in the fake target are as in the dqa."""
        self.check_instruction("move", iqm_name="move", target=self.backend._fake_target_with_moves)

    def validate_cz_loci_fake_target(self):
        """Check that the czs in the fake target are as expected."""
        # From `validate_fake_cz_loci` we know that the virtual CZs are correct
        # Now we just need to add the real CZs
        real_loci = list(
            self.dqa.gates["cz"].implementations[self.dqa.gates["cz"].default_implementation].loci,
        )
        fake_loci = [
            tuple(self.backend.index_to_qubit_name(qb) for qb in loci)
            for i, loci in self.backend._fake_target_with_moves.instructions
            if i.name == "cz"
        ]
        expected_loci = real_loci + fake_loci
        self.check_instruction("cz", expected_loci=expected_loci, target=self.backend._fake_target_with_moves)

    def check_instruction(self, qiskit_name: str, iqm_name: str = None, expected_loci=None, target=None):
        """Checks that the given instruction is defined for the expected qubits (directed)."""
        if expected_loci is None:
            if iqm_name in self.dqa.gates:
                expected_loci = list(
                    self.dqa.gates[iqm_name].implementations[self.dqa.gates[iqm_name].default_implementation].loci,
                )
            else:
                expected_loci = []
        if target is None:
            target = self.backend.target
        assert {
            tuple(self.backend.index_to_qubit_name(qb) for qb in loci)
            for (i, loci) in target.instructions
            if i.name == qiskit_name
        } == set(expected_loci)
