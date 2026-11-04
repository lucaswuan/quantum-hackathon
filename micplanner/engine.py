"""Band parsing, the frequency grid, IM enumeration, the violation checker and brute force.

All frequencies are stored as whole numbers of hertz so that "lands within 250 kHz"
never depends on floating-point rounding. Grid point k is qubit k and bit k of a plan mask.
"""

from __future__ import annotations

import re
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from itertools import combinations
from math import comb

import numpy as np

_UNITS = {"hz": 1, "khz": 1_000, "mhz": 1_000_000, "ghz": 1_000_000_000}
_NUM = r"[-+]?\d+(?:\.\d*)?|[-+]?\.\d+"
_UNIT = r"[kKmMgG]?[hH][zZ]"


def parse_freq(text, default_unit="kHz") -> int:
    """Turn "250 kHz" or "472.5 MHz" into hertz. A bare number uses `default_unit`."""
    if isinstance(text, (int, float)):
        return round(text * _UNITS[default_unit.lower()])
    m = re.fullmatch(rf"\s*({_NUM})\s*({_UNIT})?\s*", text)
    if not m:
        raise ValueError(f"Can't read a frequency from {text!r}. Try something like '250 kHz'.")
    unit = (m.group(2) or default_unit).lower()
    return round(float(m.group(1)) * _UNITS[unit])


def parse_range(text, default_unit="MHz") -> tuple[int, int]:
    """Turn "470-474 MHz" (or "470 MHz to 474 MHz") into a (low, high) pair in hertz."""
    if isinstance(text, (tuple, list)) and len(text) == 2:
        lo, hi = (parse_freq(t, default_unit) for t in text)
    else:
        m = re.fullmatch(rf"\s*({_NUM})\s*({_UNIT})?\s*(?:-|–|to)\s*({_NUM})\s*({_UNIT})?\s*", text)
        if not m:
            raise ValueError(f"Can't read a range from {text!r}. Try something like '470-474 MHz'.")
        unit = (m.group(4) or m.group(2) or default_unit).lower()
        lo_unit = (m.group(2) or unit).lower()
        lo = round(float(m.group(1)) * _UNITS[lo_unit])
        hi = round(float(m.group(3)) * _UNITS[unit])
    if hi <= lo:
        raise ValueError(f"The range {text!r} is empty: the top must be above the bottom.")
    return lo, hi


def mhz(f_hz) -> float:
    return f_hz / 1_000_000


def fmt_mhz(f_hz) -> str:
    return f"{f_hz / 1_000_000:.3f} MHz"


def fmt_khz(f_hz) -> str:
    return f"{f_hz / 1_000:g} kHz"


@dataclass
class Instance:
    """A planning problem: the allowed grid points, the mic count and the rules.

    `pairs`, `triples` and `quads` hold one entry per conflicting set of grid points
    (sorted index tuples). They are the P, T and Q sets of the cost function.
    """

    freqs: list[int]
    n_mics: int
    spacing: int
    im_guard: int
    band: tuple[int, int] | None = None
    step: int | None = None
    exclusions: list[tuple[int, int]] = field(default_factory=list)
    pairs: list[tuple[int, int]] = field(default_factory=list)
    triples: list[tuple[int, int, int]] = field(default_factory=list)
    quads: list[tuple[int, int, int, int]] = field(default_factory=list)

    @property
    def n_points(self) -> int:
        return len(self.freqs)

    def terms(self):
        """All conflicting sets, P then T then Q."""
        return list(self.pairs) + list(self.triples) + list(self.quads)

    def describe(self) -> str:
        lines = [f"{self.n_points} allowed frequencies, {self.n_mics} mics"]
        if self.band:
            lines.append(f"band {fmt_mhz(self.band[0])} to {fmt_mhz(self.band[1])} (top edge excluded), "
                         f"step {fmt_khz(self.step)}")
        for lo, hi in self.exclusions:
            lines.append(f"excluded {fmt_mhz(lo)} to {fmt_mhz(hi)}")
        lines.append(f"carrier spacing at least {fmt_khz(self.spacing)}, "
                     f"IM products must stay at least {fmt_khz(self.im_guard)} from every carrier")
        lines.append(f"conflicting sets: {len(self.pairs)} pairs, {len(self.triples)} triples, "
                     f"{len(self.quads)} quadruples")
        return "\n".join(lines)


def make_grid(band, step, exclude=()) -> tuple[list[int], tuple[int, int], int, list[tuple[int, int]]]:
    """Grid points from the bottom of the band up to (not including) the top edge.

    A point inside any exclusion range (edges included) is dropped.
    """
    lo, hi = parse_range(band)
    step_hz = parse_freq(step)
    if step_hz <= 0:
        raise ValueError("The step must be positive.")
    excl = [parse_range(e) for e in exclude]
    freqs = []
    f = lo
    while f < hi:
        if not any(a <= f <= b for a, b in excl):
            freqs.append(f)
        f += step_hz
    return freqs, (lo, hi), step_hz, excl


def _near(freqs, value, guard):
    """Indices of carriers strictly less than `guard` away from `value` (freqs sorted)."""
    return range(bisect_right(freqs, value - guard), bisect_left(freqs, value + guard))


def enumerate_conflicts(freqs, spacing, im_guard):
    """Return the P, T and Q sets for a sorted list of grid frequencies (hertz)."""
    N = len(freqs)
    pairs = [(i, j) for i, j in combinations(range(N), 2) if abs(freqs[j] - freqs[i]) < spacing]
    triples = set()
    for k in range(N):
        for l in range(N):
            if l == k:
                continue
            for m in _near(freqs, 2 * freqs[k] - freqs[l], im_guard):
                if m != k and m != l:
                    triples.add(tuple(sorted((k, l, m))))
    quads = set()
    for k, l in combinations(range(N), 2):
        for p in range(N):
            if p == k or p == l:
                continue
            for m in _near(freqs, freqs[k] + freqs[l] - freqs[p], im_guard):
                if m not in (k, l, p):
                    quads.add(tuple(sorted((k, l, p, m))))
    return pairs, sorted(triples), sorted(quads)


def build_instance(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz",
                   im_guard="250 kHz", exclude=()) -> Instance:
    freqs, band_hz, step_hz, excl = make_grid(band, step, exclude)
    if mics < 1:
        raise ValueError("Ask for at least one mic.")
    if mics > len(freqs):
        raise ValueError(f"Only {len(freqs)} frequencies are allowed, so {mics} mics can't fit.")
    inst = Instance(freqs=freqs, n_mics=mics, spacing=parse_freq(spacing), im_guard=parse_freq(im_guard),
                    band=band_hz, step=step_hz, exclusions=excl)
    inst.pairs, inst.triples, inst.quads = enumerate_conflicts(freqs, inst.spacing, inst.im_guard)
    return inst


# ---------------------------------------------------------------------------
# Checking a plan

@dataclass
class Violation:
    kind: str            # "spacing", "two-tone" or "three-tone"
    sources: tuple       # the carriers that create it (hertz)
    product: int | None  # where the product lands (hertz); None for spacing
    victim: int          # the carrier that gets hit (hertz)

    def __str__(self):
        if self.kind == "spacing":
            a, b = self.sources
            return f"spacing: {fmt_mhz(a)} and {fmt_mhz(b)} are only {fmt_khz(abs(b - a))} apart"
        if self.kind == "two-tone":
            a, b = self.sources
            rule = f"2 x {fmt_mhz(a)} - {fmt_mhz(b)}"
        else:
            a, b, c = self.sources
            rule = f"{fmt_mhz(a)} + {fmt_mhz(b)} - {fmt_mhz(c)}"
        off = self.product - self.victim
        where = "right on" if off == 0 else f"{fmt_khz(abs(off))} from"
        return f"{self.kind}: {rule} = {fmt_mhz(self.product)}, {where} the mic at {fmt_mhz(self.victim)}"


@dataclass
class CheckResult:
    plan: list[int]
    violations: list[Violation]

    @property
    def counts(self) -> dict:
        out = {"spacing": 0, "two-tone": 0, "three-tone": 0}
        for v in self.violations:
            out[v.kind] += 1
        return out

    @property
    def clean(self) -> bool:
        return not self.violations

    def report(self) -> str:
        if self.clean:
            return "No spacing problems and no third-order product within the guard of any mic."
        c = self.counts
        head = (f"{len(self.violations)} problems: {c['spacing']} spacing, "
                f"{c['two-tone']} two-tone hits, {c['three-tone']} three-tone hits")
        return "\n".join([head] + ["  " + str(v) for v in self.violations])


def check_plan(plan_hz, spacing, im_guard) -> CheckResult:
    """List every problem in a plan of carrier frequencies (hertz).

    Every product is listed separately, so one evenly spaced triple shows up as two two-tone hits.
    Works for any frequencies, not just grid points.
    """
    f = sorted(int(x) for x in plan_hz)
    out = []
    for a, b in combinations(f, 2):
        if b - a < spacing:
            out.append(Violation("spacing", (a, b), None, b))
    for a in f:
        for b in f:
            if a == b:
                continue
            prod = 2 * a - b
            for c in _near(f, prod, im_guard):
                if f[c] not in (a, b):
                    out.append(Violation("two-tone", (a, b), prod, f[c]))
    for a, b in combinations(f, 2):
        for c in f:
            if c in (a, b):
                continue
            prod = a + b - c
            for d in _near(f, prod, im_guard):
                if f[d] not in (a, b, c):
                    out.append(Violation("three-tone", (a, b, c), prod, f[d]))
    return CheckResult(f, out)


def check_indices(inst: Instance, idx) -> CheckResult:
    return check_plan([inst.freqs[i] for i in idx], inst.spacing, inst.im_guard)


def cost_of(inst: Instance, idx, w3=1.0) -> float:
    """C(x) for a plan given as grid indices: one unit per conflicting pair, w3 per triple or quadruple."""
    s = set(idx)
    c = sum(1 for t in inst.pairs if s.issuperset(t))
    c += w3 * sum(1 for t in inst.triples if s.issuperset(t))
    c += w3 * sum(1 for t in inst.quads if s.issuperset(t))
    return c


# ---------------------------------------------------------------------------
# Plans as bit masks, and brute force

def plan_masks(N, n) -> np.ndarray:
    """Every n-of-N plan as an integer bit mask, in lexicographic order of the index tuples."""
    return np.array([sum(1 << i for i in c) for c in combinations(range(N), n)], dtype=np.int64)


def mask_to_indices(mask) -> tuple[int, ...]:
    mask = int(mask)
    return tuple(i for i in range(mask.bit_length()) if mask >> i & 1)


def term_masks(terms) -> np.ndarray:
    return np.array([sum(1 << i for i in t) for t in terms], dtype=np.int64)


def cost_vector(inst: Instance, masks, w3=1.0) -> np.ndarray:
    """C(x) for many plans at once (any bit masks, not only weight-n ones)."""
    masks = np.asarray(masks, dtype=np.int64)
    out = np.zeros(len(masks))
    for terms, w in ((inst.pairs, 1.0), (inst.triples, w3), (inst.quads, w3)):
        if not terms:
            continue
        tm = term_masks(terms)
        for start in range(0, len(masks), 4096):
            chunk = masks[start:start + 4096, None]
            out[start:start + 4096] += w * ((chunk & tm[None, :]) == tm[None, :]).sum(axis=1)
    return out


def spacing_ok_vector(inst: Instance, masks) -> np.ndarray:
    masks = np.asarray(masks, dtype=np.int64)
    if not inst.pairs:
        return np.ones(len(masks), dtype=bool)
    tm = term_masks(inst.pairs)
    return ~((masks[:, None] & tm[None, :]) == tm[None, :]).any(axis=1)


@dataclass
class BruteForceResult:
    n_plans: int
    n_spaced: int
    n_clean: int
    best_cost: float
    best_plans: list[tuple[int, ...]]
    seconds: float

    @property
    def clean_share(self) -> float:
        return self.n_clean / self.n_plans

    @property
    def clean_share_spaced(self) -> float:
        return self.n_clean / self.n_spaced if self.n_spaced else 0.0


def brute_force(inst: Instance, w3=1.0) -> BruteForceResult:
    """Score every n-mic plan. Exact, and fine up to a few hundred thousand plans."""
    t0 = time.perf_counter()
    masks = plan_masks(inst.n_points, inst.n_mics)
    costs = cost_vector(inst, masks, w3)
    spaced = spacing_ok_vector(inst, masks)
    best = costs.min()
    best_plans = [mask_to_indices(m) for m in masks[costs == best]]
    secs = time.perf_counter() - t0
    return BruteForceResult(len(masks), int(spaced.sum()), int((costs == 0).sum()), float(best),
                            best_plans, secs)


def count_third_order_products(n_carriers: int) -> dict:
    """How many third-order products n carriers create (before asking where they land)."""
    two = n_carriers * (n_carriers - 1)
    three = comb(n_carriers, 2) * (n_carriers - 2)
    return {"two-tone": two, "three-tone": three, "total": two + three}
