"""The cost function as a HUBO, its Pauli-Z form, the diagonal check and the QUBO size counter."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np
from qiskit.quantum_info import SparsePauliOp, Statevector

from .engine import Instance, cost_vector


def hubo_terms(inst: Instance, w3=1.0) -> dict[tuple, float]:
    """C(x) as {variables: coefficient}: 1 per close pair, w3 per IM triple or quadruple."""
    terms = {t: 1.0 for t in inst.pairs}
    for t in list(inst.triples) + list(inst.quads):
        terms[t] = terms.get(t, 0.0) + w3
    return terms


def hubo_to_pauli(terms: dict[tuple, float], n_qubits: int) -> SparsePauliOp:
    """Substitute x_k = (1 - Z_k)/2 and collect a diagonal Pauli-Z polynomial.

    A product of w variables becomes 2^-w times the sum over all its subsets A of (-1)^|A| Z_A.
    The identity term is kept so that the operator's diagonal equals C(x) exactly.
    """
    coeffs = defaultdict(float)
    for S, c in terms.items():
        w = len(S)
        for r in range(w + 1):
            for A in combinations(S, r):
                coeffs[A] += c * (-1) ** r / 2 ** w
    sparse = [("Z" * len(A), list(A), v) for A, v in sorted(coeffs.items(), key=lambda kv: (len(kv[0]), kv[0]))
              if abs(v) > 1e-12]
    return SparsePauliOp.from_sparse_list(sparse, num_qubits=n_qubits)


def cost_operator(inst: Instance, w3=1.0) -> SparsePauliOp:
    return hubo_to_pauli(hubo_terms(inst, w3), inst.n_points)


def z_strings_by_weight(op: SparsePauliOp) -> dict[int, int]:
    """How many Z-strings of each weight the operator has (identity left out)."""
    weights = op.paulis.z.sum(axis=1)
    return dict(sorted(Counter(int(w) for w in weights if w > 0).items()))


def naive_cnot_count(op: SparsePauliOp) -> int:
    """CNOTs if every weight-w Z rotation is built as a CNOT ladder: 2(w - 1) each."""
    weights = op.paulis.z.sum(axis=1)
    return int(sum(2 * (w - 1) for w in weights if w > 1))


def pauli_diagonal(op: SparsePauliOp, masks) -> np.ndarray:
    """The diagonal of a Z-only operator at the given basis states, computed directly."""
    masks = np.asarray(masks, dtype=np.int64)
    z = op.paulis.z
    out = np.zeros(len(masks))
    bits = (masks[:, None] >> np.arange(op.num_qubits)[None, :]) & 1
    for row, c in zip(z, op.coeffs):
        parity = bits[:, row].sum(axis=1) & 1
        out += c.real * (1 - 2 * parity)
    return out


def check_diagonal(inst: Instance, op: SparsePauliOp, w3=1.0, exhaustive_max=12, n_spot=64, seed=11) -> dict:
    """Compare the operator's diagonal with the classical cost.

    Up to `exhaustive_max` qubits, every basis state is checked with Qiskit's own matrix.
    Above that, `n_spot` random basis states are checked with Statevector expectation values,
    and every basis state is also checked with a direct parity calculation.
    """
    n = op.num_qubits
    if op.paulis.x.any():
        raise ValueError("The cost operator should only contain Z terms.")
    if n <= exhaustive_max:
        masks = np.arange(2 ** n, dtype=np.int64)
        diag = op.to_matrix(sparse=True).diagonal().real
        classical = cost_vector(inst, masks, w3)
        return {"method": f"all {2 ** n} basis states, Qiskit to_matrix",
                "max_error": float(np.abs(diag - classical).max()), "states": 2 ** n}
    rng = np.random.default_rng(seed)
    spot = rng.choice(2 ** n, size=n_spot, replace=False)
    spot_vals = np.array([Statevector.from_int(int(i), 2 ** n).expectation_value(op).real for i in spot])
    spot_err = float(np.abs(spot_vals - cost_vector(inst, spot, w3)).max())
    masks = np.arange(2 ** n, dtype=np.int64)
    full_err = float(np.abs(pauli_diagonal(op, masks) - cost_vector(inst, masks, w3)).max())
    return {"method": f"{n_spot} random states via Statevector, plus all {2 ** n} by direct parity",
            "max_error": max(spot_err, full_err), "spot_error": spot_err, "full_error": full_err,
            "states": 2 ** n}


def quadratize_greedy(terms, n_vars, rng: random.Random | None = None) -> tuple[int, list]:
    """Count the auxiliary variables a QUBO needs under greedy Rosenberg substitution.

    Repeat until every term has at most two variables: find the pair of variables that
    appears together in the most terms of degree three or more, add a new variable
    y = x_i x_j (Rosenberg's penalty makes this hold at the optimum), and put y in place
    of that pair in every term that contains both. Ties go to the smallest pair, or to a
    random one when `rng` is given.
    """
    mons = [tuple(sorted(t)) for t in terms if len(t) > 2]
    nxt, subs = n_vars, []
    while mons:
        cnt = Counter()
        for m in mons:
            cnt.update(combinations(m, 2))
        best = max(cnt.values())
        cands = sorted(p for p, c in cnt.items() if c == best)
        i, j = rng.choice(cands) if rng else cands[0]
        y, nxt = nxt, nxt + 1
        subs.append(((i, j), y, best))
        new = []
        for m in mons:
            if i in m and j in m:
                m = tuple(sorted([v for v in m if v not in (i, j)] + [y]))
            if len(m) > 2:
                new.append(m)
        mons = new
    return len(subs), subs


def qubo_size(inst: Instance, trials=200, seed=5) -> dict:
    """Variables a QUBO would need: deterministic greedy, plus the range over random tie-breaks."""
    terms = inst.terms()
    det, _ = quadratize_greedy(terms, inst.n_points)
    rng = random.Random(seed)
    tries = [quadratize_greedy(terms, inst.n_points, rng)[0] for _ in range(trials)]
    n = inst.n_points
    return {"qubits": n, "aux": det, "variables": n + det,
            "best_variables": n + min(tries), "worst_variables": n + max(tries), "trials": trials}
