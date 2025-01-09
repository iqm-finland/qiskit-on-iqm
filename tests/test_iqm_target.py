"""Testing IQM transpilation.
"""

import pytest

from iqm.qiskit_iqm.fake_backends.fake_adonis import IQMFakeAdonis
from iqm.qiskit_iqm.fake_backends.fake_aphrodite import IQMFakeAphrodite
from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb


@pytest.mark.parametrize(
    "backend,restriction",
    [
        (IQMFakeAdonis(), ["QB4", "QB3", "QB1"]),
        (IQMFakeAphrodite(), ["QB18", "QB17", "QB25"]),
        (IQMFakeDeneb(), ["QB5", "QB3", "QB1", "COMP_R"]),
    ],
)
def test_target_from_restricted_qubits(backend, restriction):
    """Test that the restricted target is properly created."""
    restriction_idxs = [backend.qubit_name_to_index(qubit) for qubit in restriction]
    for restricted in [restriction, restriction_idxs]:  # Check both string and integer restrictions
        restricted_target = backend.target.restrict_to_qubits(restricted)  # Restrict from IQMTarget
        restricted_edges = restricted_target.build_coupling_map().get_edges()
        assert restricted_target.num_qubits == len(restricted)

        assert set(restricted_edges) == set(
            backend.restrict_to_qubits(restricted).build_coupling_map().get_edges()
        )  # Restrict from backend

        # Check if the edges are allowed in both the backend and the restricted target
        for edge in restricted_edges:
            translated_edge = (
                backend.qubit_name_to_index(restriction[edge[0]]),
                backend.qubit_name_to_index(restriction[edge[1]]),
            )
            assert translated_edge in backend.coupling_map.get_edges()
