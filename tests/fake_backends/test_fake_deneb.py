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

"""Testing fake Deneb backend.
"""
import re

import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer.noise.noise_model import NoiseModel

from iqm.qiskit_iqm import IQMCircuit, transpile_to_IQM
from iqm.qiskit_iqm.fake_backends.fake_deneb import IQMFakeDeneb


def test_iqm_fake_deneb():
    backend = IQMFakeDeneb()
    assert backend.num_qubits == 7
    assert backend.name == "IQMFakeDenebBackend"


def test_iqm_fake_deneb_connectivity(deneb_coupling_map):
    backend = IQMFakeDeneb()
    assert set(backend.coupling_map.get_edges()) == deneb_coupling_map


def test_iqm_fake_deneb_noise_model_instantiated():
    backend = IQMFakeDeneb()
    assert isinstance(backend.noise_model, NoiseModel)


def test_move_gate_sandwich_interrupted_with_single_qubit_gate():
    backend = IQMFakeDeneb()
    no_qubits = 6
    comp_r = QuantumRegister(1, "comp_r")  # Computational resonator
    q = QuantumRegister(no_qubits, "q")  # Qubits
    c = ClassicalRegister(no_qubits, "c")  # Classical register, used for readout
    qc = IQMCircuit(comp_r, q, c)

    qc.move(1, 0)
    qc.x(1)
    qc.move(1, 0)
    qc.measure(q, c)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Operations to qubits Qubit(QuantumRegister(7, 'q'), 1) while their states are moved to a resonator."
        ),
    ):
        backend.run(transpile(qc, backend=backend), shots=1000)


def test_move_gate_sandwich_interrupted_with_second_move_gate():
    backend = IQMFakeDeneb()
    no_qubits = 6
    comp_r = QuantumRegister(1, "comp_r")  # Computational resonator
    q = QuantumRegister(no_qubits, "q")  # Qubits
    c = ClassicalRegister(no_qubits, "c")  # Classical register, used for readout
    qc = IQMCircuit(comp_r, q, c)

    qc.move(1, 0)
    qc.move(2, 0)
    qc.move(1, 0)
    qc.measure(q, c)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Cannot apply MOVE on Qubit(QuantumRegister(6, 'q'), 1) because COMP_R already holds the state of "
            + "Qubit(QuantumRegister(6, 'q'), 0)."
        ),
    ):
        backend.run(qc, shots=1000)


def test_move_gate_not_closed():
    backend = IQMFakeDeneb()
    no_qubits = 6
    comp_r = QuantumRegister(1, "comp_r")  # Computational resonator
    q = QuantumRegister(no_qubits, "q")  # Qubits
    c = ClassicalRegister(no_qubits, "c")  # Classical register, used for readout
    qc = IQMCircuit(comp_r, q, c)

    qc.move(1, 0)
    qc.measure(q, c)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "The following resonators are still holding qubit states at the end of the circuit: "
            + "Qubit(QuantumRegister(6, 'q'), 0)."
        ),
    ):
        backend.run(qc, shots=1000)


def test_simulate_ghz_circuit_with_iqm_fake_deneb_noise_model_():
    backend = IQMFakeDeneb()
    no_qubits = 6
    comp_r = QuantumRegister(1, "comp_r")  # Computational resonator
    q = QuantumRegister(no_qubits, "q")  # Qubits
    c = ClassicalRegister(no_qubits, "c")  # Classical register, used for readout
    qc = IQMCircuit(comp_r, q, c)

    qc.h(1)
    qc.move(1, 0)  # MOVE into the resonator

    for i in range(2, no_qubits + 1):
        qc.cx(0, i)
    qc.move(1, 0)  # MOVE out of the resonator

    qc.barrier()
    qc.measure(q, c)

    job = backend.run(transpile(qc, backend=backend), shots=1000)

    res = job.result()
    counts = res.get_counts()

    # see that 000000 and 111111 states have most counts
    largest_two = sorted(counts.items(), key=lambda x: x[1])[-2:]

    for count in largest_two:
        assert count[0] in ["000000", "111111"]


def test_transpile_to_IQM_for_ghz_with_fake_deneb_noise_model():
    backend = IQMFakeDeneb()
    num_qb = 6
    qc = QuantumCircuit(6)
    qc.h(0)
    for qb in range(1, num_qb):
        qc.cx(0, qb)
    qc.measure_all()

    transpiled_qc = transpile_to_IQM(qc, backend=backend)

    job = backend.run(transpiled_qc, shots=1000)
    res = job.result()
    counts = res.get_counts()

    # see that 000000 and 111111 states have most counts
    largest_two = sorted(counts.items(), key=lambda x: x[1])[-2:]

    for count in largest_two:
        assert count[0] in ["000000", "111111"]


def test_transpiling_works_but_backend_run_doesnt_with_unsupported_gates():
    backend = IQMFakeDeneb()
    num_qb = 6
    qc_list = []
    for _ in range(4):
        qc_list.append(QuantumCircuit(num_qb))

    qc_list[0].h(1)
    qc_list[1].x(2)
    qc_list[2].y(3)
    qc_list[3].z(4)

    for qc in qc_list:
        backend.run(transpile_to_IQM(qc, backend=backend), shots=1000)

        with pytest.raises(ValueError, match=r"^Operation '[A-Za-z]' is not supported by the backend."):
            backend.run(qc, shots=1000)
