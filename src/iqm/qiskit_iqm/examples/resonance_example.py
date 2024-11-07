from iqm.qiskit_iqm import IQMProvider, transpile_to_IQM
from qiskit import QuantumCircuit
from qiskit import visualization

server_url = "https://cocos.resonance.meetiqm.com/<QUANTUM COMPUTER>"  # For example https://cocos.resonance.meetiqm.com/garnet
api_token = "<INSERT YOUR TOKEN>"

SHOTS = 1000

# Define quantum circuit
num_qb = 5
qc = QuantumCircuit(num_qb)

qc.h(0)
for qb in range(1, num_qb):
    qc.cx(0, qb)
qc.barrier()
qc.measure_all()

# Initialize backend
backend = IQMProvider(server_url, token=api_token).get_backend()

# Transpile circuit
qc_transpiled = transpile_to_IQM(qc, backend)
print(qc_transpiled.draw(output="text"))

# Run circuit
job = backend.run(qc_transpiled, shots=SHOTS)
print(job.result().get_counts())

# Plot result
result_dict = job.result().get_counts()
visualization.plot_histogram(result_dict)