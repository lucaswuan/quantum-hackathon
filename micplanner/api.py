"""plan_mics: describe the venue in plain terms, get back a checked plan, a report and a spectrum."""

from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass, field

import matplotlib.pyplot as plt

from .cost import cost_operator
from .engine import CheckResult, Instance, build_instance, check_indices, cost_of, fmt_khz, fmt_mhz, mask_to_indices
from .plots import plot_spectrum
from .quantum import FastQAOA, TuneResult, build_ansatz, compile_ansatz, sample, tune


@dataclass
class PlanResult:
    plan_mhz: list[float]
    plan_indices: tuple[int, ...]
    clean: bool
    check: CheckResult
    instance: Instance
    tuning: list[TuneResult]
    counts: dict[int, int]
    shots: int
    clean_share: float
    random_share: float
    plan_share: float
    seconds: dict = field(default_factory=dict)
    figure: object = None
    csv_path: str | None = None
    report: str = ""

    def __repr__(self):
        return f"PlanResult({', '.join(f'{f:.3f}' for f in self.plan_mhz)} MHz, clean={self.clean})"


def plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz", im_guard="250 kHz", exclude=(),
              layers=3, objective="cvar", alpha=0.1, shots=8000, seed=2026, csv_path="plan.csv", show=True,
              max_points=20, title=None) -> PlanResult:
    """Plan wireless mic frequencies with no third-order intermodulation hits.

    band, step, spacing, im_guard and exclude take plain strings such as "470-474 MHz" or "250 kHz".
    Every allowed frequency becomes one qubit. QAOA (Dicke start, XY mixer, angles tuned on an
    exact NumPy simulation) runs on Qiskit's StatevectorSampler, and the most common IM-free
    sample becomes the plan. The plan is then checked product by product with ordinary arithmetic.
    """
    t_start = time.perf_counter()
    inst = build_instance(band, mics, step, spacing, im_guard, exclude)
    if inst.n_points > max_points:
        raise ValueError(f"That gives {inst.n_points} allowed frequencies, which means {inst.n_points} qubits. "
                         f"This simulator demo stops at {max_points}. Use a larger step or a narrower band.")
    op = cost_operator(inst)
    fast = FastQAOA(inst)

    t0 = time.perf_counter()
    tuning = tune(fast, max_p=layers, kind=objective, alpha=alpha)
    best = tuning[-1]
    t_tune = time.perf_counter() - t0

    t0 = time.perf_counter()
    compiled = compile_ansatz(build_ansatz(op, mics, layers), measure=True)
    counts = sample(compiled, best.gammas, best.betas, shots=shots, seed=seed)
    t_sample = time.perf_counter() - t0

    scored = sorted(((cost_of(inst, mask_to_indices(m)), -c, m) for m, c in counts.items()))
    clean_masks = {m for c, _, m in scored if c == 0}
    clean_share = sum(counts[m] for m in clean_masks) / shots
    plan_idx = mask_to_indices(scored[0][2])
    check = check_indices(inst, plan_idx)
    plan_hz = [inst.freqs[i] for i in plan_idx]
    plan_share = counts[scored[0][2]] / shots
    random_share = float(fast.clean.mean())

    lines = [f"Mic plan: {mics} mics, {inst.n_points} allowed frequencies ({inst.n_points} qubits)",
             f"Rules: mics at least {fmt_khz(inst.spacing)} apart, no third-order product within "
             f"{fmt_khz(inst.im_guard)} of a mic"]
    for lo, hi in inst.exclusions:
        lines.append(f"Kept clear: {fmt_mhz(lo)} to {fmt_mhz(hi)}")
    lines += [f"  Mic {i + 1}: {fmt_mhz(f)}" for i, f in enumerate(plan_hz)]
    lines.append("Check: " + check.report())
    lines.append(f"How it was found: QAOA with {layers} layers ({best.label()} objective), {shots:,} samples "
                 f"from Qiskit's StatevectorSampler.")
    lines.append(f"  {clean_share:.1%} of samples were IM-free plans. A plan picked at random is IM-free "
                 f"{random_share:.2%} of the time (counted over all {fast.dim:,} plans).")
    if check.clean:
        lines.append(f"  This plan was the most common clean sample ({plan_share:.1%} of samples).")
    else:
        lines.append("  No IM-free plan turned up in the samples. This is the best sample, with its problems "
                     "listed above. Try more layers or shots, or confirm with micplanner.brute_force.")

    fig = None
    if show:
        fig, ax = plt.subplots(figsize=(11, 3.4))
        plot_spectrum(plan_hz, inst.spacing, inst.im_guard, ax=ax, band=inst.band, exclusions=inst.exclusions,
                      grid=inst.freqs, title=title or "Planned mics and their third-order products")
        fig.tight_layout()

    if csv_path:
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["mic", "frequency_mhz"])
            for i, f in enumerate(plan_hz):
                w.writerow([i + 1, f"{f / 1e6:.3f}"])
        lines.append(f"Saved {csv_path}")

    report = "\n".join(lines)
    print(report)
    return PlanResult([f / 1e6 for f in plan_hz], plan_idx, check.clean, check, inst, tuning, counts, shots,
                      clean_share, random_share, plan_share,
                      {"tune": t_tune, "sample": t_sample, "total": time.perf_counter() - t_start},
                      fig, csv_path, report)
