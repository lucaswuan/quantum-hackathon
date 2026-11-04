"""Classical baselines: brute force, greedy, simulated annealing, uniform random and an exact MILP."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .engine import Instance, brute_force, cost_of, cost_vector, term_masks


@dataclass
class BaselineResult:
    name: str
    plan: tuple[int, ...] | None
    cost: float | None
    clean: bool | None
    seconds: float
    note: str = ""


def run_brute_force(inst: Instance) -> BaselineResult:
    bf = brute_force(inst)
    plan = bf.best_plans[0]
    return BaselineResult("Brute force (exact)", plan, bf.best_cost, bf.best_cost == 0, bf.seconds,
                          f"{bf.n_clean} of {bf.n_plans} plans are IM-free")


def greedy(inst: Instance, first: int | None = None) -> BaselineResult:
    """Add one mic at a time, always the frequency that adds the fewest new conflicts.

    Ties go to the lowest frequency, so with no `first` the plan starts at the bottom of the band.
    """
    t0 = time.perf_counter()
    chosen = [] if first is None else [first]
    while len(chosen) < inst.n_mics:
        options = [k for k in range(inst.n_points) if k not in chosen]
        best = min(options, key=lambda k: (cost_of(inst, chosen + [k]), k))
        chosen.append(best)
    plan = tuple(sorted(chosen))
    c = cost_of(inst, plan)
    label = "Greedy" if first is None else f"Greedy from point {first}"
    return BaselineResult(label, plan, c, c == 0, time.perf_counter() - t0)


def greedy_all_starts(inst: Instance) -> tuple[int, list[BaselineResult]]:
    """Greedy started from every grid point in turn. Returns (clean count, results)."""
    runs = [greedy(inst, k) for k in range(inst.n_points)]
    return sum(r.clean for r in runs), runs


def simulated_annealing(inst: Instance, runs=50, steps=1000, t_start=2.0, t_end=0.05, seed=11) -> dict:
    """Swap moves (one mic out, one free point in) keep the mic count fixed.

    Each move's cost change is worked out locally from the terms that touch the two points.
    Returns the best plan over all runs and how many runs ended on a clean plan.
    """
    t0 = time.perf_counter()
    rng = random.Random(seed)
    N, n = inst.n_points, inst.n_mics
    terms = inst.terms()
    weights = [1.0] * len(terms)
    masks = [int(m) for m in term_masks(terms)]
    touching = [[(masks[i], weights[i]) for i, t in enumerate(terms) if k in t] for k in range(N)]

    def local(S, k):
        return sum(w for m, w in touching[k] if S & m == m)

    best_plan, best_cost, clean_runs = None, math.inf, 0
    for _ in range(runs):
        pts = rng.sample(range(N), n)
        S = sum(1 << k for k in pts)
        cur = cost_of(inst, pts)
        run_best = cur
        for s in range(steps):
            T = t_start * (t_end / t_start) ** (s / max(steps - 1, 1))
            a = rng.choice([k for k in range(N) if S >> k & 1])
            b = rng.choice([k for k in range(N) if not S >> k & 1])
            S_out = S & ~(1 << a)
            delta = local(S_out | (1 << b), b) - local(S, a)
            if delta <= 0 or rng.random() < math.exp(-delta / T):
                S, cur = S_out | (1 << b), cur + delta
                if cur < run_best:
                    run_best = cur
                if cur < best_cost:
                    best_cost, best_plan = cur, tuple(k for k in range(N) if S >> k & 1)
            if run_best == 0:
                break
        clean_runs += run_best == 0
    secs = time.perf_counter() - t0
    return {"result": BaselineResult("Simulated annealing", best_plan, best_cost, best_cost == 0, secs,
                                     f"{clean_runs} of {runs} runs ended clean"),
            "clean_runs": clean_runs, "runs": runs}


def uniform_random(inst: Instance, shots=8000, seed=99) -> dict:
    """Plans drawn uniformly at random, which is what the Dicke state alone would give."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    picks = np.array([rng.choice(inst.n_points, inst.n_mics, replace=False) for _ in range(shots)])
    masks = (np.int64(1) << picks).sum(axis=1)
    costs = cost_vector(inst, masks)
    share = float((costs == 0).mean())
    best = int(np.argmin(costs))
    plan = tuple(sorted(int(k) for k in picks[best]))
    secs = time.perf_counter() - t0
    return {"result": BaselineResult("Uniform random", plan, float(costs[best]), bool(costs[best] == 0), secs,
                                     f"{share:.2%} of {shots} random plans are IM-free"),
            "share": share, "costs": costs}


def milp_solve(inst: Instance) -> BaselineResult:
    """Exact integer program: one 0/1 variable per conflicting set, forced on when all its points are used."""
    t0 = time.perf_counter()
    N, terms = inst.n_points, inst.terms()
    T = len(terms)
    c = np.concatenate([np.zeros(N), np.ones(T)])
    A = np.zeros((T + 1, N + T))
    lo = np.full(T + 1, -np.inf)
    hi = np.zeros(T + 1)
    A[0, :N] = 1
    lo[0] = hi[0] = inst.n_mics
    for i, t in enumerate(terms):
        A[i + 1, list(t)] = 1
        A[i + 1, N + i] = -1
        hi[i + 1] = len(t) - 1
    res = milp(c, constraints=LinearConstraint(A, lo, hi), integrality=np.ones(N + T), bounds=Bounds(0, 1))
    secs = time.perf_counter() - t0
    plan = tuple(int(k) for k in np.nonzero(np.round(res.x[:N]))[0])
    cost = cost_of(inst, plan)
    return BaselineResult("Integer program (SciPy milp)", plan, cost, cost == 0, secs, res.message)
