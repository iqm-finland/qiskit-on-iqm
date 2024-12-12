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
def test_transpiling_with_restricted_qubits(backend, restriction):
    """Test that the transpiled circuit only uses the qubits specified in the restriction."""
    restriction_idxs = [backend.qubit_name_to_index(qubit) for qubit in restriction]
    for restricted in [restriction, restriction_idxs]:
        print("Restriction:", restricted)
        restricted_target = backend.target.restrict_to_qubits(restricted)
        assert restricted_target.num_qubits == len(restricted)

        for edge in restricted_target.build_coupling_map().get_edges():
            translated_edge = (
                backend.qubit_name_to_index(restriction[edge[0]]),
                backend.qubit_name_to_index(restriction[edge[1]]),
            )
            assert translated_edge in backend.coupling_map.get_edges()
