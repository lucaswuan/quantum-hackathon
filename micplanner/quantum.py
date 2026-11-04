"""Dicke start, XY mixer, QAOA circuit, angle tuning, sampling and the exact NumPy fast path.

Conventions: grid point k is qubit k, and a plan is the integer whose bit k is 1 when a mic
sits on point k. That is also the Statevector index and the Qiskit bitstring read as binary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from math import acos, comb, sqrt

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import PauliEvolutionGate, RYGate, qaoa_ansatz
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import SparsePauliOp, Statevector
from scipy.optimize import minimize

from .engine import Instance, cost_vector, plan_masks

BASIS = ["cx", "rz", "sx", "x"]


# ---------------------------------------------------------------------------
# Dicke state (Bärtschi and Eidenbenz 2019)

def _scs(qc: QuantumCircuit, m: int, j: int):
    """Split and cyclic shift on the first m qubits, for weights up to j.

    Paper positions 1..m map to qubits 0..m-1. Gate (i) handles weight 1, gate (ii) weight l.
    """
    a, b = m - 2, m - 1
    qc.cx(a, b)
    qc.cry(2 * acos(sqrt(1 / m)), b, a)
    qc.cx(a, b)
    for l in range(2, j + 1):
        a, c, b = m - l - 1, m - l, m - 1
        qc.cx(a, b)
        qc.append(RYGate(2 * acos(sqrt(l / m))).control(2, annotated=False), [b, c, a])
        qc.cx(a, b)


def dicke_circuit(n: int, k: int) -> QuantumCircuit:
    """Prepare |D^n_k>, the equal superposition of every n-qubit string with k ones."""
    qc = QuantumCircuit(n, name=f"Dicke({n},{k})")
    if k == 0:
        return qc
    for q in range(n - k, n):
        qc.x(q)
    if k == n:
        return qc
    for m in range(n, 1, -1):
        _scs(qc, m, min(k, m - 1))
    return qc


def dicke_vector(n: int, k: int) -> np.ndarray:
    v = np.zeros(2 ** n)
    v[plan_masks(n, k)] = 1 / sqrt(comb(n, k))
    return v


# ---------------------------------------------------------------------------
# XY ring mixer

def mixer_groups(n: int) -> list[list[tuple[int, int]]]:
    """Ring neighbours split into groups of disjoint pairs: even pairs, then odd pairs.

    With an even number of qubits the wrap-around pair joins the odd group. With an odd
    number it overlaps both, so it gets a group of its own.
    """
    if n < 2:
        return []
    if n == 2:
        return [[(0, 1)]]
    even = [(i, i + 1) for i in range(0, n - 1, 2)]
    odd = [(i, i + 1) for i in range(1, n - 1, 2)]
    wrap = [(n - 1, 0)]
    return [even, odd + wrap] if n % 2 == 0 else [even, odd, wrap]


def xy_mixer_operator(n: int) -> SparsePauliOp:
    """H_XY = 1/2 sum over ring neighbours of (XX + YY), listed group by group.

    The listing order matters: Qiskit synthesizes exp(-i beta H) term by term in this order,
    which gives exp(-i beta H_odd) exp(-i beta H_even) exactly (each group's terms commute).
    """
    sparse = [(P + P, [i, j], 0.5) for group in mixer_groups(n) for i, j in group for P in "XY"]
    return SparsePauliOp.from_sparse_list(sparse, num_qubits=n)


def xy_mixer_circuit(n: int, beta: float) -> QuantumCircuit:
    """The same mixer written as explicit RXX and RYY gates, used to cross-check the synthesis."""
    qc = QuantumCircuit(n, name="XY mixer")
    for group in mixer_groups(n):
        for i, j in group:
            qc.rxx(beta, i, j)
            qc.ryy(beta, i, j)
    return qc


# ---------------------------------------------------------------------------
# The QAOA circuit

def drop_identity(op: SparsePauliOp) -> SparsePauliOp:
    """Remove the constant term; it only adds a global phase to exp(-i gamma H)."""
    keep = op.paulis.z.any(axis=1) | op.paulis.x.any(axis=1)
    return SparsePauliOp(op.paulis[keep], op.coeffs[keep])


def build_ansatz(cost_op: SparsePauliOp, n_mics: int, reps: int) -> QuantumCircuit:
    """Dicke start, then reps layers of exp(-i gamma H_C) followed by the XY mixer."""
    n = cost_op.num_qubits
    return qaoa_ansatz(drop_identity(cost_op), reps=reps, initial_state=dicke_circuit(n, n_mics),
                       mixer_operator=xy_mixer_operator(n))


def angle_binding(circuit: QuantumCircuit, gammas, betas) -> dict:
    """Map the ansatz's β[i] and γ[i] parameters to values by name, not by position."""
    values = {}
    for p in circuit.parameters:
        name = p.name
        if name.startswith("γ["):
            values[p] = float(gammas[int(name[2:-1])])
        elif name.startswith("β["):
            values[p] = float(betas[int(name[2:-1])])
        else:
            raise ValueError(f"Unexpected parameter {name}")
    return values


def compile_ansatz(ansatz: QuantumCircuit, optimization_level=1, measure=False, seed=17) -> QuantumCircuit:
    qc = ansatz.copy()
    if measure:
        qc.measure_all()
    return transpile(qc, basis_gates=BASIS, optimization_level=optimization_level, seed_transpiler=seed)


def circuit_state(compiled: QuantumCircuit, gammas, betas) -> np.ndarray:
    bound = compiled.assign_parameters(angle_binding(compiled, gammas, betas))
    return Statevector(bound).data


def sample(compiled_measured: QuantumCircuit, gammas, betas, shots=8000, seed=2026) -> dict[int, int]:
    """Run the real circuit on StatevectorSampler. Returns {plan mask: count}."""
    bound = compiled_measured.assign_parameters(angle_binding(compiled_measured, gammas, betas))
    result = StatevectorSampler(seed=seed).run([bound], shots=shots).result()
    counts = result[0].data.meas.get_counts()
    return {int(b, 2): c for b, c in counts.items()}


# ---------------------------------------------------------------------------
# Exact NumPy fast path on the n-mic subspace

class FastQAOA:
    """Exact QAOA simulation restricted to the plans with exactly n mics.

    The cost layer is a diagonal phase. The mixer is applied pair by pair in the same
    group order as the circuit: on the states where the two bits differ, each pair gate
    mixes |01> and |10> with cos(beta) and -i sin(beta). Nothing is approximated.
    """

    def __init__(self, inst: Instance, w3=1.0):
        self.inst = inst
        self.n_qubits = inst.n_points
        self.masks = plan_masks(inst.n_points, inst.n_mics)
        self.dim = len(self.masks)
        self.cost = cost_vector(inst, self.masks, w3)
        self.clean = self.cost == 0
        order = np.argsort(self.masks)
        sorted_masks = self.masks[order]
        self.groups = []
        for group in mixer_groups(self.n_qubits):
            maps = []
            for a, b in group:
                differ = ((self.masks >> a) & 1) != ((self.masks >> b) & 1)
                idx = np.nonzero(differ)[0]
                partner = self.masks[idx] ^ ((1 << a) | (1 << b))
                par = order[np.searchsorted(sorted_masks, partner)]
                maps.append((idx, par))
            self.groups.append(maps)
        self.psi0 = np.full(self.dim, 1 / sqrt(self.dim), dtype=complex)
        self.n_evals = 0

    def state(self, gammas, betas) -> np.ndarray:
        psi = self.psi0.copy()
        for g, b in zip(gammas, betas):
            psi *= np.exp(-1j * g * self.cost)
            c, s = np.cos(b), -1j * np.sin(b)
            for maps in self.groups:
                for idx, par in maps:
                    psi[idx] = c * psi[idx] + s * psi[par]
        self.n_evals += 1
        return psi

    def probs(self, gammas, betas) -> np.ndarray:
        return np.abs(self.state(gammas, betas)) ** 2

    def expectation(self, probs) -> float:
        return float(probs @ self.cost)

    def cvar(self, probs, alpha) -> float:
        """Mean cost of the best alpha share of the distribution."""
        order = np.argsort(self.cost, kind="stable")
        p, c = probs[order], self.cost[order]
        cum = np.cumsum(p)
        take = np.minimum(p, np.maximum(alpha - (cum - p), 0))
        return float(take @ c / alpha)

    def objective(self, gammas, betas, kind="mean", alpha=0.2) -> float:
        pr = self.probs(gammas, betas)
        return self.expectation(pr) if kind == "mean" else self.cvar(pr, alpha)

    def clean_prob(self, gammas, betas) -> float:
        return float(self.probs(gammas, betas)[self.clean].sum())


@dataclass
class TuneResult:
    p: int
    objective: str
    alpha: float | None
    gammas: np.ndarray
    betas: np.ndarray
    value: float
    clean_prob: float
    expected_cost: float
    history: list = field(default_factory=list)
    n_evals: int = 0
    seconds: float = 0.0

    def label(self):
        return "mean" if self.objective == "mean" else f"CVaR (alpha={self.alpha})"


def landscape_p1(fast: FastQAOA, gammas, betas, kind="mean", alpha=0.2):
    """Objective and IM-free probability on a gamma by beta grid, for one layer."""
    obj = np.zeros((len(betas), len(gammas)))
    clean = np.zeros_like(obj)
    for i, b in enumerate(betas):
        for j, g in enumerate(gammas):
            pr = fast.probs([g], [b])
            obj[i, j] = fast.expectation(pr) if kind == "mean" else fast.cvar(pr, alpha)
            clean[i, j] = pr[fast.clean].sum()
    return obj, clean


def _run_cobyla(fast, x0, p, kind, alpha, maxiter):
    hist = []

    def f(x):
        v = fast.objective(x[:p], x[p:], kind, alpha)
        hist.append(v)
        return v

    res = minimize(f, x0, method="COBYLA", options={"maxiter": maxiter, "rhobeg": 0.2})
    return res.x, res.fun, hist


def _interp(x):
    """Zhou et al. INTERP: stretch p optimal angles to a p + 1 starting point."""
    p = len(x)
    out = np.zeros(p + 1)
    for i in range(p + 1):
        left = x[i - 1] if i - 1 >= 0 else 0.0
        right = x[i] if i < p else 0.0
        out[i] = i / p * left + (p - i) / p * right
    return out


def tune(fast: FastQAOA, max_p=3, kind="mean", alpha=0.2, n_random=6, maxiter=500, seed=7,
         grid=48) -> list[TuneResult]:
    """Tune angles layer by layer with COBYLA on the fast path.

    p = 1 starts from the best point of a grid scan. Each deeper p starts from INTERP of the
    previous optimum plus a few seeded random points. Returns one result per p.
    """
    rng = np.random.default_rng(seed)
    results = []
    prev = None
    for p in range(1, max_p + 1):
        t0 = time.perf_counter()
        fast.n_evals = 0
        if p == 1:
            gs = np.linspace(0.02, np.pi, grid)
            bs = np.linspace(0.02, np.pi, grid)
            obj, _ = landscape_p1(fast, gs, bs, kind, alpha)
            i, j = np.unravel_index(np.argmin(obj), obj.shape)
            starts = [np.array([gs[j], bs[i]])]
        else:
            g, b = prev.gammas, prev.betas
            starts = [np.concatenate([_interp(g), _interp(b)])]
        starts += [np.concatenate([rng.uniform(0, np.pi / 2, p), rng.uniform(0, np.pi / 2, p)])
                   for _ in range(n_random)]
        best = None
        for x0 in starts:
            x, val, hist = _run_cobyla(fast, x0, p, kind, alpha, maxiter)
            if best is None or val < best[1] - 1e-12:
                best = (x, val, hist)
        x, val, hist = best
        pr = fast.probs(x[:p], x[p:])
        res = TuneResult(p, kind, alpha if kind != "mean" else None, x[:p].copy(), x[p:].copy(), float(val),
                         float(pr[fast.clean].sum()), fast.expectation(pr), hist, fast.n_evals,
                         time.perf_counter() - t0)
        results.append(res)
        prev = res
    return results


def compare_with_circuit(fast: FastQAOA, compiled: QuantumCircuit, gammas, betas) -> dict:
    """Run the compiled circuit as a Statevector and compare it with the fast path."""
    t0 = time.perf_counter()
    full = circuit_state(compiled, gammas, betas)
    secs = time.perf_counter() - t0
    sub = full[fast.masks]
    ref = fast.state(gammas, betas)
    leak = 1 - float(np.sum(np.abs(sub) ** 2))
    overlap = np.vdot(ref, sub)
    phase = overlap / abs(overlap)
    return {"fidelity": float(abs(overlap) ** 2), "leakage": leak,
            "max_prob_diff": float(np.max(np.abs(np.abs(sub) ** 2 - np.abs(ref) ** 2))),
            "max_amp_diff": float(np.max(np.abs(sub - phase * ref))), "seconds": secs}


# ---------------------------------------------------------------------------
# Resource card

def resource_card(cost_op: SparsePauliOp, n_mics: int, reps: int, optimization_level=1, seed=17) -> dict:
    """Qubits, Z-strings and transpiled gate counts for each piece and for the full circuit."""
    from .cost import z_strings_by_weight

    n = cost_op.num_qubits

    def counts(qc):
        t0 = time.perf_counter()
        t = transpile(qc, basis_gates=BASIS, optimization_level=optimization_level, seed_transpiler=seed)
        ops = t.count_ops()
        return {"cx": int(ops.get("cx", 0)), "depth": t.depth(), "size": t.size(),
                "transpile_s": time.perf_counter() - t0}

    cost_layer = QuantumCircuit(n)
    cost_layer.append(PauliEvolutionGate(drop_identity(cost_op), time=0.37), range(n))
    mixer = QuantumCircuit(n)
    mixer.append(PauliEvolutionGate(xy_mixer_operator(n), time=0.41), range(n))
    full = build_ansatz(cost_op, n_mics, reps)
    return {"qubits": n, "z_strings": z_strings_by_weight(cost_op), "reps": reps,
            "basis": BASIS, "optimization_level": optimization_level,
            "dicke": counts(dicke_circuit(n, n_mics)), "cost_layer": counts(cost_layer),
            "mixer_layer": counts(mixer), "full": counts(full)}
