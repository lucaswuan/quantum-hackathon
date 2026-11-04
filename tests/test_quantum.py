import numpy as np
import pytest
from qiskit import transpile
from qiskit.quantum_info import Operator, SparsePauliOp, Statevector

from micplanner.cost import cost_operator
from micplanner.engine import build_instance
from micplanner.quantum import (BASIS, FastQAOA, build_ansatz, compare_with_circuit, compile_ansatz, dicke_circuit,
                                dicke_vector, mixer_groups, sample, tune, xy_mixer_circuit, xy_mixer_operator)


@pytest.mark.parametrize("n", range(1, 9))
def test_dicke_state_is_exact(n):
    for k in range(n + 1):
        sv = Statevector(dicke_circuit(n, k)).data
        assert np.allclose(sv, dicke_vector(n, k), atol=1e-10), (n, k)


def test_dicke_16_5_after_transpiling():
    qc = transpile(dicke_circuit(16, 5), basis_gates=BASIS, optimization_level=1)
    sv = Statevector(qc).data
    assert abs(np.vdot(dicke_vector(16, 5), sv)) ** 2 == pytest.approx(1, abs=1e-9)


@pytest.mark.parametrize("n", [4, 5, 6, 7])
def test_mixer_keeps_the_mic_count(n):
    U = Operator(transpile(xy_mixer_circuit(n, 0.63), basis_gates=BASIS)).data
    weights = np.array([bin(i).count("1") for i in range(2 ** n)])
    leak = np.abs(U[weights[:, None] != weights[None, :]])
    assert leak.max() < 1e-10


@pytest.mark.parametrize("n", [4, 5, 6])
def test_synthesized_mixer_is_the_group_product(n):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import PauliEvolutionGate
    from scipy.linalg import expm
    beta = 0.41
    qc = QuantumCircuit(n)
    qc.append(PauliEvolutionGate(xy_mixer_operator(n), time=beta), range(n))
    U = Operator(transpile(qc, basis_gates=BASIS, optimization_level=1)).data
    target = np.eye(2 ** n, dtype=complex)
    for group in mixer_groups(n):
        H = SparsePauliOp.from_sparse_list([(P + P, [i, j], 0.5) for i, j in group for P in "XY"], n).to_matrix()
        target = expm(-1j * beta * H) @ target
    phase = U[0, 0] / target[0, 0]
    assert np.allclose(U, phase * target, atol=1e-9)
    assert np.allclose(Operator(xy_mixer_circuit(n, beta)).data, target, atol=1e-9)


def test_fast_path_matches_circuit_small():
    inst = build_instance("470-472 MHz", mics=3)  # 8 points
    fast = FastQAOA(inst)
    compiled = compile_ansatz(build_ansatz(cost_operator(inst), 3, reps=2))
    rng = np.random.default_rng(3)
    for _ in range(3):
        g, b = rng.uniform(0, np.pi, 2), rng.uniform(0, np.pi, 2)
        res = compare_with_circuit(fast, compiled, g, b)
        assert res["fidelity"] == pytest.approx(1, abs=1e-9)
        assert res["leakage"] < 1e-10


def test_odd_ring_fast_path_matches_circuit():
    inst = build_instance("470-471.75 MHz", mics=2)  # 7 points, three mixer groups
    assert inst.n_points == 7
    fast = FastQAOA(inst)
    compiled = compile_ansatz(build_ansatz(cost_operator(inst), 2, reps=1))
    res = compare_with_circuit(fast, compiled, [0.7], [0.4])
    assert res["fidelity"] == pytest.approx(1, abs=1e-9)


def test_p0_is_uniform_and_tuning_beats_it():
    inst = build_instance("470-472 MHz", mics=3)
    fast = FastQAOA(inst)
    base = fast.clean.mean()
    assert fast.clean_prob([], []) == pytest.approx(base)
    res = tune(fast, max_p=2, kind="mean", n_random=2, grid=16)
    assert res[-1].expected_cost < fast.cost.mean()


def test_sampler_counts_are_plans_with_three_mics():
    inst = build_instance("470-472 MHz", mics=3)
    compiled = compile_ansatz(build_ansatz(cost_operator(inst), 3, reps=1), measure=True)
    counts = sample(compiled, [0.5], [0.3], shots=500, seed=1)
    assert sum(counts.values()) == 500
    assert all(bin(m).count("1") == 3 for m in counts)
