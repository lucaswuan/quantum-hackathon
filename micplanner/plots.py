"""Spectrum plot, histogram, convergence and the other figures.

Colours follow one validated palette: blue for mics and the QAOA series, orange for the
second series, grey for harmless products and the random baseline, and the reserved
critical red only for products that land on a mic (always with an x marker and a label).
"""

from __future__ import annotations

from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from .engine import check_plan, count_third_order_products

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BAND = "#f0efec"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
CRITICAL = "#d03b3b"
RAMP = ["#86b6ef", "#2a78d6", "#104281"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK, "axes.titlesize": 13,
    "axes.titleweight": "bold", "legend.frameon": False, "legend.labelcolor": INK2,
})


def _tidy(ax, grid_axis="y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)


def third_order_products(plan_hz):
    """Every third-order product of a plan as (frequency, kind)."""
    f = sorted(plan_hz)
    out = [(2 * a - b, "two-tone") for a in f for b in f if a != b]
    out += [(a + b - c, "three-tone") for a, b in combinations(f, 2) for c in f if c not in (a, b)]
    return out


def plot_spectrum(plan_hz, spacing, im_guard, ax=None, band=None, exclusions=(), grid=None, title=None,
                  xlim=None, legend=True, label_mics=True):
    """Mics as tall blue stems, IM products as short grey stems, products on a mic in red with an x."""
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 3.4))
    res = check_plan(plan_hz, spacing, im_guard)
    hit_products = {v.product for v in res.violations if v.product is not None}
    prods = third_order_products(plan_hz)
    if band:
        ax.axvspan(band[0] / 1e6, band[1] / 1e6, color=BAND, zorder=0, lw=0)
        ax.text(band[0] / 1e6 + 0.05, 1.52, "planning band", ha="left", va="top", color=MUTED, fontsize=9.5)
    for lo, hi in exclusions:
        ax.axvspan(lo / 1e6 - 0.06, hi / 1e6 + 0.06, facecolor=GRID, edgecolor=AXIS, hatch="//", lw=0, zorder=0.5)
        ax.text((lo + hi) / 2e6, 1.52, "excluded", ha="center", va="top", color=INK2, fontsize=9.5)
    if grid is not None:
        ax.plot(np.array(grid) / 1e6, np.zeros(len(grid)), "|", color=MUTED, ms=7, zorder=1)
    for p in sorted({p for p, _ in prods}):
        hit = p in hit_products
        ax.vlines(p / 1e6, 0, 0.55 if hit else 0.4, color=CRITICAL if hit else MUTED, lw=2 if hit else 1.4,
                  zorder=2 if hit else 1.5)
        if hit:
            ax.plot(p / 1e6, 0.62, "x", color=CRITICAL, ms=9, mew=2.2, zorder=4)
    prev, raised = None, False
    for f in sorted(plan_hz):
        ax.vlines(f / 1e6, 0, 1, color=BLUE, lw=2.6, zorder=3)
        ax.plot(f / 1e6, 1, "o", color=BLUE, ms=8, zorder=3, mec=SURFACE, mew=2)
        if label_mics:
            # Lift every other label when neighbours are close, so the numbers never collide.
            raised = (not raised) if prev is not None and f - prev < 600_000 else False
            ax.text(f / 1e6, 1.2 if raised else 1.06, f"{f / 1e6:.2f}", ha="center", va="bottom",
                    fontsize=9.5, color=INK2)
        prev = f
    for v in res.violations:
        if v.kind == "spacing":
            a, b = v.sources
            ax.plot([a / 1e6, b / 1e6], [0.9, 0.9], color=CRITICAL, lw=2.5, zorder=4)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    _tidy(ax, grid_axis=None)
    ax.set_ylim(-0.05, 1.56)
    ax.set_xlabel("Frequency (MHz)")
    if xlim:
        ax.set_xlim(*xlim)
    if title:
        ax.set_title(title, loc="left")
    if legend:
        handles = [Line2D([], [], color=BLUE, lw=2.6, marker="o", ms=7, label="Mic"),
                   Line2D([], [], color=MUTED, lw=1.4, label="Third-order IM product"),
                   Line2D([], [], color=CRITICAL, lw=2, marker="x", ms=8, mew=2,
                          label=f"Product within {im_guard / 1e3:g} kHz of a mic (a hit)")]
        ax.legend(handles=handles, loc="upper center", ncol=3, fontsize=9.5, bbox_to_anchor=(0.5, -0.3))
    return ax, res


def plot_ghost_example():
    """Two mics, their two two-tone products, and where a third mic would get hit."""
    f1, f2 = 470_500_000, 471_250_000
    g1, g2 = 2 * f1 - f2, 2 * f2 - f1
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axvspan(469.4, 472.6, color=BAND, lw=0, zorder=0)
    for f, name in ((f1, "Mic 1"), (f2, "Mic 2")):
        ax.vlines(f / 1e6, 0, 1, color=BLUE, lw=2.6)
        ax.plot(f / 1e6, 1, "o", color=BLUE, ms=8, mec=SURFACE, mew=2)
        ax.text(f / 1e6, 1.08, f"{name}\n{f / 1e6:.2f} MHz", ha="center", va="bottom", color=INK, fontsize=10)
    for g, rule in ((g1, "2 x f1 - f2"), (g2, "2 x f2 - f1")):
        ax.vlines(g / 1e6, 0, 0.5, color=MUTED, lw=2)
        ax.text(g / 1e6, 0.56, f"{rule}\n= {g / 1e6:.2f} MHz", ha="center", va="bottom", color=INK2, fontsize=10)
    ax.annotate("A third mic tuned here\nwould pick up this ghost", xy=(g2 / 1e6 + 0.02, 0.3),
                xytext=(g2 / 1e6 + 0.18, 0.18), color=CRITICAL, fontsize=10, va="center",
                arrowprops=dict(arrowstyle="->", color=CRITICAL, lw=1.5))
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    _tidy(ax, grid_axis=None)
    ax.set_xlim(469.4, 472.9)
    ax.set_ylim(0, 1.5)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_title("Two mics create two ghost signals", loc="left")
    fig.tight_layout()
    return fig


def plot_product_growth(max_n=40):
    n = np.arange(3, max_n + 1)
    two = np.array([count_third_order_products(k)["two-tone"] for k in n])
    three = np.array([count_third_order_products(k)["three-tone"] for k in n])
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(n, three, color=ORANGE, lw=2)
    ax.plot(n, two, color=BLUE, lw=2)
    ax.set_yscale("log")
    ax.text(max_n + 0.6, three[-1], f"three-tone\n{three[-1]:,}", color=INK2, va="center", fontsize=10)
    ax.text(max_n + 0.6, two[-1], f"two-tone\n{two[-1]:,}", color=INK2, va="center", fontsize=10)
    for k in (3, 5, 10):
        i = k - 3
        ax.plot([k, k], [two[i], three[i]], "o", color=INK2, ms=4)
        ax.text(k + 0.8, three[i] * 1.5, f"{k} mics: {two[i] + three[i]:,}", ha="left", va="bottom",
                color=INK2, fontsize=9.5)
    ax.set_xlim(2, max_n + 7)
    ax.set_xlabel("Mics transmitting at once")
    ax.set_ylabel("Third-order products (log scale)")
    ax.set_title("Products grow roughly with the cube of the mic count", loc="left")
    ax.legend(handles=[Line2D([], [], color=ORANGE, lw=2, label="f_a + f_b - f_c"),
                       Line2D([], [], color=BLUE, lw=2, label="2 f_a - f_b")], loc="upper left")
    _tidy(ax)
    fig.tight_layout()
    return fig


def plot_histogram(qaoa_costs, qaoa_weights, random_costs, random_weights, labels=("QAOA", "Uniform random")):
    """Share of plans by number of conflicting sets, QAOA beside uniform random."""
    top = int(max(np.max(qaoa_costs), np.max(random_costs)))
    bins = np.arange(top + 1)
    q = np.array([np.sum(np.asarray(qaoa_weights)[np.asarray(qaoa_costs) == b]) for b in bins])
    r = np.array([np.sum(np.asarray(random_weights)[np.asarray(random_costs) == b]) for b in bins])
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    w = 0.4
    ax.bar(bins - w / 2, q * 100, w, color=BLUE, label=labels[0], ec=SURFACE, lw=2)
    ax.bar(bins + w / 2, r * 100, w, color=MUTED, label=labels[1], ec=SURFACE, lw=2)
    top_y = max(q.max(), r.max()) * 100
    ax.annotate(f"IM-free: {labels[0].split(',')[0]} {q[0]:.1%}, random {r[0]:.2%}",
                xy=(-w / 2, q[0] * 100 + 0.5), xytext=(-w / 2 - 0.08, top_y + 6), ha="left", va="bottom",
                color=INK, fontsize=10.5, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1, relpos=(0.03, 0)))
    ax.set_ylim(0, top_y + 12)
    ax.set_xticks(bins)
    ax.set_xlabel("Conflicting sets in the plan (0 = IM-free)")
    ax.set_ylabel("Share of plans (%)")
    ax.set_title("QAOA shifts the odds toward clean plans", loc="left")
    ax.legend(loc="upper right")
    _tidy(ax)
    fig.tight_layout()
    return fig


def plot_convergence(results, title="COBYLA convergence on the fast path"):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for r, c in zip(results, RAMP + [INK] * 10):
        h = np.minimum.accumulate(r.history)
        ax.plot(np.arange(1, len(h) + 1), h, color=c, lw=2, label=f"p = {r.p}")
        ax.text(len(h) + 5, h[-1], f"p = {r.p}", color=INK2, va="center", fontsize=10)
    ax.set_xlabel("Objective evaluations (best start for each p)")
    ax.set_ylabel(f"Best {results[0].label()} so far")
    ax.set_title(title, loc="left")
    ax.legend(loc="upper right")
    _tidy(ax)
    fig.tight_layout()
    return fig


def plot_clean_vs_p(by_objective: dict, baseline: float, sampled=None):
    """Exact IM-free probability against the number of layers for each objective."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    colours = [BLUE, ORANGE]
    for (name, results), c in zip(by_objective.items(), colours):
        ps = [r.p for r in results]
        vals = [100 * r.clean_prob for r in results]
        ax.plot(ps, vals, color=c, lw=2, marker="o", ms=8, mec=SURFACE, mew=2, label=name)
        ax.text(ps[-1] + 0.12, vals[-1], name, color=INK2, va="center", fontsize=10)
    ax.axhline(100 * baseline, color=MUTED, lw=1.5)
    ax.text(1, 100 * baseline + 0.3, f"uniform random {baseline:.2%}", color=INK2, fontsize=10, va="bottom")
    if sampled is not None:
        p, share = sampled
        ax.plot(p, 100 * share, "s", ms=10, mfc="none", mec=INK, mew=1.8, label="sampled on the circuit")
    ax.set_xticks(sorted({r.p for rs in by_objective.values() for r in rs}))
    ax.set_xlabel("QAOA layers p")
    ax.set_ylabel("Chance a sample is IM-free (%)")
    ax.set_title("More layers, more clean plans", loc="left")
    ax.legend(loc="upper left")
    ax.set_xlim(0.7, max(r.p for rs in by_objective.values() for r in rs) + 0.9)
    _tidy(ax)
    fig.tight_layout()
    return fig


def plot_side_by_side(top, bottom, spacing, im_guard, band=None, grid=None, xlim=None):
    """Two plans stacked: each item is (plan_hz, title)."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True)
    for i, (ax, (plan, title)) in enumerate(zip(axes, (top, bottom))):
        plot_spectrum(plan, spacing, im_guard, ax=ax, band=band, grid=grid, title=title, xlim=xlim, legend=i == 1)
    axes[0].set_xlabel("")
    fig.tight_layout()
    return fig
