"""Build figures/demo.gif, the animated tour of the planner shown at the top of the README.

Three scenes, about 20 seconds, looping:
  1. The problem: two mics make two ghost signals, and five evenly spaced mics take 20 hits.
  2. The quantum planner: the plan_mics(...) call, 16 frequencies as 16 qubits, and QAOA raising
     the IM-free share from 0.55% (random pick) to 7.1% (p = 3, 8,000 shots), then the measurement.
  3. The result: the mics move to the QAOA plan, the ghosts move with them, and the hits drop to 0.

Every number comes from a fresh plan_mics run (same seeds as the notebook) and the project's own
hit rule, so the GIF matches the README. Run from the repo root (about a minute):

    python tools/make_demo_gif.py
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, Patch, Rectangle
from PIL import Image

from micplanner.api import plan_mics
from micplanner.plots import AXIS, BAND, BLUE, CRITICAL, GRID, INK, INK2, MUTED, SURFACE
from micplanner.quantum import FastQAOA

OUT = os.path.join(ROOT, "figures", "demo.gif")
W, H, DPI, FPS = 1000, 540, 100, 20
FADE = 0.4                                  # crossfade between scenes, seconds
XLIM = (466, 477.5)                         # MHz, wide enough for every product of both plans
NEWCOMER = (0, 3, 6, 9, 12)                 # grid indices, as in make_figures.py: 470.00 to 473.00 MHz
LIGHT_BLUE = "#86b6ef"
MONO = "DejaVu Sans Mono"
STEPS = ("The problem", "The quantum planner", "The result")


# ---------------------------------------------------------------------------
# Data

def gather():
    """Run the planner once and keep what the animation needs."""
    with contextlib.redirect_stdout(io.StringIO()):
        r = plan_mics(show=False, csv_path=None)
    inst = r.instance
    fast = FastQAOA(inst)
    n = inst.n_points
    bits = ((fast.masks[:, None] >> np.arange(n)) & 1).astype(float)
    bins = np.arange(int(fast.cost.max()) + 1)

    def stage(probs):
        hist = np.array([probs[fast.cost == b].sum() for b in bins])
        return hist, probs @ bits

    uniform = np.full(fast.dim, 1 / fast.dim)
    stages = [stage(uniform)] + [stage(fast.probs(t.gammas, t.betas)) for t in r.tuning[:-1]]
    sampled = np.zeros(fast.dim)
    where = {int(m): i for i, m in enumerate(fast.masks)}
    for m, c in r.counts.items():
        sampled[where[int(m)]] += c / r.shots
    stages.append(stage(sampled))           # the last layer count is shown as sampled on the circuit
    return dict(
        freqs=inst.freqs, guard=inst.im_guard, band=inst.band, n_plans=fast.dim,
        newcomer=[inst.freqs[i] for i in NEWCOMER], plan=[inst.freqs[i] for i in r.plan_indices],
        plan_idx=set(r.plan_indices), bins=bins, random=stages[0][0],
        hists=[s[0] for s in stages], marginals=[s[1] for s in stages],
        shares=[s[0][0] for s in stages], shots=r.shots, layers=len(r.tuning),
    )


def third_order(f):
    """Every third-order product of carriers f as (frequency, source indices), as check_plan lists them."""
    n = len(f)
    out = [(2 * f[a] - f[b], (a, b)) for a in range(n) for b in range(n) if a != b]
    out += [(f[a] + f[b] - f[c], (a, b, c)) for a, b in combinations(range(n), 2) for c in range(n) if c not in (a, b)]
    return out


def victims(f, value, sources, guard):
    """Carriers other than the sources that sit strictly less than `guard` from a product (the hit rule)."""
    return [d for d in range(len(f)) if d not in sources and abs(round(value) - round(f[d])) < guard]


# ---------------------------------------------------------------------------
# Easing and small helpers

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ramp(t, t0, dur):
    return clamp((t - t0) / dur)


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def pop(x):
    """Ease out with a small overshoot, for markers that pop in."""
    x = clamp(x)
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def mix(c1, c2, t):
    a, b = np.array(matplotlib.colors.to_rgb(c1)), np.array(matplotlib.colors.to_rgb(c2))
    return tuple(a + (b - a) * clamp(t))


def pct(v):
    return f"{v:.2%}" if v < 0.01 else f"{v:.1%}"


# ---------------------------------------------------------------------------
# Frame furniture

def new_frame(fig):
    fig.clf()
    ov = fig.add_axes([0, 0, 1, 1])
    ov.set_xlim(0, W)
    ov.set_ylim(H, 0)
    ov.axis("off")
    ov.set_zorder(5)
    ov.patch.set_alpha(0)
    return ov


def data_axes(fig, x0, y0, x1, y1):
    """Axes placed in pixels from the top-left corner."""
    ax = fig.add_axes([x0 / W, 1 - y1 / H, (x1 - x0) / W, (y1 - y0) / H])
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    return ax


def header(ov, step, captions, t):
    """Step chip, progress bars, and the caption. `captions` is [(start_time, text), ...]."""
    ov.add_patch(Circle((51, 33), 11, color=BLUE, lw=0))
    ov.text(51, 33.5, str(step + 1), color="white", ha="center", va="center", fontsize=10.5, fontweight="bold")
    ov.text(70, 33.5, STEPS[step], color=BLUE, ha="left", va="center", fontsize=11.5, fontweight="bold")
    ov.text(W - 40, 30, "IM-free wireless mic planner", color=MUTED, ha="right", va="center", fontsize=9.5)
    for i in range(3):
        ov.add_patch(Rectangle((W - 40 - (3 - i) * 44 + 4, 44), 40, 4, color=BLUE if i <= step else GRID, lw=0))
    for k, (start, text) in enumerate(captions):
        end = captions[k + 1][0] if k + 1 < len(captions) else 1e9
        a = ease(ramp(t, start, 0.3)) * (1 - ease(ramp(t, end - 0.2, 0.2)))
        if a > 0:
            ov.text(40, 78 + 6 * (1 - a), text, color=INK, alpha=a, ha="left", va="center",
                    fontsize=15, fontweight="bold")


def footer_legend(fig, handles):
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), bbox_to_anchor=(0.5, 0.012),
               fontsize=10, frameon=False, handlelength=1.8, columnspacing=2.2, labelcolor=INK2)


SPECTRUM_LEGEND = [
    Line2D([], [], color=BLUE, lw=2.6, marker="o", ms=7, mec=SURFACE, mew=1.5, label="Mic"),
    Line2D([], [], color=MUTED, lw=1.6, label="Ghost signal (third-order IM product)"),
    Line2D([], [], color=CRITICAL, lw=0, marker="x", ms=8, mew=2.2, label="Ghost within 250 kHz of a mic: a hit"),
]


def hit_counter(ov, hits, alpha, sub, ok=0.0):
    """'Ghost hits' readout at the top right of the spectrum: red while hits remain, blue at zero."""
    if alpha <= 0:
        return
    x = W - 46
    ov.text(x, 128, "Ghost hits", color=INK2, ha="right", va="center", fontsize=10.5, alpha=alpha)
    colour = mix(CRITICAL, BLUE, ok)
    label = f"{hits}" if ok < 0.5 else "0 ✓"
    ov.text(x, 162, label, color=colour, ha="right", va="center", fontsize=28, fontweight="bold", alpha=alpha)
    for k, (text, a) in enumerate(sub):
        if a > 0:
            ov.text(x, 196, text, color=INK2, ha="right", va="center", fontsize=9.5, alpha=alpha * a)


def spectrum(fig, d, f, mic_alpha, prods, labels=(), show_grid=False, mic_text=None):
    """Draw the band, the ghosts and the mics.

    f: mic frequencies (Hz). mic_alpha: 0..1 per mic (grows the stem).
    prods: [(freq_hz, grow 0..1, hit 0..1)]. labels: [(x_mhz, y, text, alpha, size)].
    mic_text: per-mic label alpha, or None for no frequency labels.
    """
    ax = data_axes(fig, 40, 104, W - 40, 432)
    ax.set_xlim(*XLIM)
    ax.set_ylim(-0.03, 1.55)
    ax.set_yticks([])
    ax.set_xticks(range(466, 478, 2))
    ax.tick_params(axis="x", colors=MUTED, labelsize=10.5, length=4, color=AXIS)
    ax.set_xlabel("Frequency (MHz)", color=INK2, fontsize=10.5, labelpad=5)
    lo, hi = d["band"][0] / 1e6, d["band"][1] / 1e6
    ax.axvspan(lo, hi, color=BAND, lw=0, zorder=0)
    ax.text(lo + 0.07, 1.49, "planning band", ha="left", va="top", color=MUTED, fontsize=9.5)
    if show_grid:
        ax.plot(np.array(d["freqs"]) / 1e6, np.zeros(len(d["freqs"])), "|", color=MUTED, ms=7, zorder=1)
    for v, grow, hit in sorted(prods, key=lambda p: p[2]):
        if grow <= 0:
            continue
        h = 0.4 * ease_out(grow) + 0.15 * hit
        ax.vlines(v / 1e6, 0, h, color=mix(MUTED, CRITICAL, hit), lw=1.6 + 0.6 * hit, zorder=2 + hit)
        if hit > 0:
            ax.plot(v / 1e6, 0.62, "x", color=CRITICAL, ms=9.5 * pop(hit), mew=2.4, zorder=5)
    prev, raised = None, False
    for i in np.argsort(f):
        a = mic_alpha[i]
        if a <= 0:
            continue
        top = ease_out(a)
        x = f[i] / 1e6
        ax.vlines(x, 0, top, color=BLUE, lw=2.8, zorder=4, alpha=clamp(3 * a))
        ax.plot(x, top, "o", color=BLUE, ms=9, mec=SURFACE, mew=2, zorder=4, alpha=clamp(3 * a))
        if mic_text is not None and mic_text[i] > 0:
            raised = (not raised) if prev is not None and x - prev < 0.6 else False
            ax.text(x, 1.2 if raised else 1.07, f"{x:.2f}", ha="center", va="bottom", fontsize=10,
                    color=INK2, alpha=mic_text[i])
        prev = x
    for x, y, text, a, size in labels:
        if a > 0:
            ax.text(x, y, text, ha="center", va="bottom", color=INK2, fontsize=size, alpha=a)
    return ax


# ---------------------------------------------------------------------------
# Scene 1: the problem

S1_LEN = 6.6
S1_APPEAR = {1: 0.35, 2: 0.7, 0: 3.0, 3: 3.3, 4: 3.6}   # mic index in NEWCOMER -> time it switches on


def scene_problem(fig, d, t):
    ov = new_frame(fig)
    header(ov, 0, [(0, "Two mics on air create ghost signals (intermodulation)."),
                   (2.8, "Space five mics evenly and the ghosts land right on them.")], t)
    f = d["newcomer"]
    on = [S1_APPEAR[i] for i in range(len(f))]
    mic_alpha = [ramp(t, s, 0.45) for s in on]
    prods, hits = [], 0
    for v, src in third_order(f):
        t_p = max(on[s] for s in src) + (0.6 if set(src) <= {1, 2} else 0.3)
        grow = ramp(t, t_p, 0.5)
        hit = 0.0
        for vic in victims(f, v, src, d["guard"]):
            h = ramp(t, max(t_p, on[vic]) + 0.2, 0.3)
            hits += h >= 0.5
            hit = max(hit, h)
        prods.append((v, grow, hit))
    intro = ramp(t, 0.35, 0.4) * (1 - ramp(t, 2.6, 0.3))
    ghosts = ramp(t, 1.3, 0.4) * (1 - ramp(t, 2.6, 0.3))
    f1, f2 = f[1] / 1e6, f[2] / 1e6
    labels = [(f1, 1.07, "$f_1$", intro, 13), (f2, 1.07, "$f_2$", intro, 13),
              (2 * f1 - f2, 0.47, "$2f_1 - f_2$", ghosts, 11.5), (2 * f2 - f1, 0.47, "$2f_2 - f_1$", ghosts, 11.5)]
    spectrum(fig, d, f, mic_alpha, prods, labels)
    hit_counter(ov, hits, ease(ramp(t, 2.8, 0.3)), [("evenly spaced plan", 1)])
    footer_legend(fig, SPECTRUM_LEGEND)


# ---------------------------------------------------------------------------
# Scene 2: the quantum planner

S2_LEN = 8.4
CODE = [("plan_mics", INK), ("(band=", INK2), ('"470-474 MHz"', BLUE), (", mics=", INK2), ("5", BLUE), (")", INK2)]
S2_TYPE = (0.3, 1.2)                         # start, duration of the typing
S2_QUBITS = 1.6
S2_HIST = 2.5
S2_LAYERS = (3.0, 4.0, 5.0)                 # start of each morph, 0.65 s each
S2_MEASURE = 6.1


def scene_quantum(fig, d, t):
    ov = new_frame(fig)
    header(ov, 1, [(0, "Describe the band in plain words. Each frequency becomes a qubit."),
                   (2.6, "QAOA shifts probability toward the IM-free plans."),
                   (S2_MEASURE - 0.1, "Measure: the most common IM-free sample is the plan.")], t)

    # The call, typed out.
    total = sum(len(s) for s, _ in CODE)
    shown = int(round(total * ramp(t, *S2_TYPE)))
    cw = 13 * DPI / 72 * 0.602                # DejaVu Sans Mono advance width at 13 pt
    ov.add_patch(FancyBboxPatch((40, 106), 40 + cw * (total + 5), 40, boxstyle="round,pad=0,rounding_size=7",
                                fc=BAND, ec=GRID, lw=1))
    x = 58
    ov.text(x, 126.5, ">>>", color=MUTED, fontsize=13, family=MONO, va="center")
    x += cw * 4
    left = shown
    for s, c in CODE:
        part = s[:max(0, left)]
        if part:
            ov.text(x, 126.5, part, color=c, fontsize=13, family=MONO, va="center")
        x += cw * len(part)
        left -= len(s)
    if t < S2_QUBITS + 0.4 and int(t * 2.5) % 2 == 0:
        ov.add_patch(Rectangle((x + 1, 117), 2, 19, color=INK, lw=0))

    # Stage of the QAOA morph: s runs 0 (Dicke start) to 3 (p = 3).
    s = sum(ease(ramp(t, t0, 0.65)) for t0 in S2_LAYERS)
    k = min(int(s), len(d["hists"]) - 2)
    w = s - k
    hist = d["hists"][k] * (1 - w) + d["hists"][k + 1] * w
    marg = d["marginals"][k] * (1 - w) + d["marginals"][k + 1] * w
    share = d["shares"][k] * (1 - w) + d["shares"][k + 1] * w

    # 16 frequencies -> 16 qubits; filled by P(qubit = 1), then measured.
    n = len(d["freqs"])
    gap, r = 38, 12
    x0 = W / 2 + 20 - gap * (n - 1) / 2
    y = 196
    meas = ease(ramp(t, S2_MEASURE, 0.5))
    row = ease(ramp(t, S2_QUBITS, 0.3))
    ov.text(40, y, f"{n} qubits", color=INK2, fontsize=11.5, fontweight="bold", va="center", alpha=row)
    ov.text(40, y + 20, "one per frequency", color=MUTED, fontsize=9.5, va="center", alpha=row)
    for i in range(n):
        a = pop(ramp(t, S2_QUBITS + 0.03 * i, 0.3))
        if a <= 0:
            continue
        cx = x0 + gap * i
        one = i in d["plan_idx"]
        fill = mix(mix(SURFACE, BLUE, marg[i]), BLUE if one else SURFACE, meas)
        edge = mix(BLUE, BLUE if one else AXIS, meas)
        ov.add_patch(Circle((cx, y), r * a, fc=fill, ec=edge, lw=1.4))
        if meas > 0:
            ov.text(cx, y + 0.5, "1" if one else "0", color="white" if one else MUTED, alpha=meas, fontsize=10,
                    fontweight="bold", ha="center", va="center", family=MONO)
        if one:
            ov.text(cx, y + 27, f"{d['freqs'][i] / 1e6:.2f}", color=mix(MUTED, BLUE, meas), ha="center",
                    va="center", fontsize=9, alpha=row if i == 0 else meas)
    ov.text(x0 + gap * (n - 1), y + 27, f"{d['freqs'][-1] / 1e6:.2f} MHz", color=MUTED, ha="center", va="center",
            fontsize=9, alpha=row * (1 - meas))

    # Histogram of conflicts per plan: QAOA beside a uniform random pick.
    ha = ease(ramp(t, S2_HIST, 0.4))
    if ha > 0:
        bins = d["bins"]
        ax = data_axes(fig, 92, 272, W - 40, 448)
        ax.axvspan(-0.5, 0.5, color=BLUE, alpha=0.07 * ha, lw=0)
        ax.bar(bins - 0.2, hist * 100 * ha, 0.38, color=BLUE, lw=0)
        ax.bar(bins + 0.2, d["random"] * 100 * ha, 0.38, color=MUTED, lw=0)
        ax.set_xlim(-0.6, bins[-1] + 0.6)
        ax.set_ylim(0, 50)
        ax.set_xticks(bins)
        ax.set_yticks([0, 25, 50])
        ax.set_yticklabels(["0", "25%", "50%"])
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, labelsize=10, length=0, pad=4)
        ax.set_xlabel(f"Conflicts in the plan (0 = IM-free), over all {d['n_plans']:,} possible plans",
                      color=INK2, fontsize=10.5, labelpad=5)
        for sp in ax.spines.values():
            sp.set_alpha(ha)

        # Layer stepper.
        names = ["start"] + [f"p = {p}" for p in range(1, d["layers"] + 1)]
        ov.text(92, 260, "QAOA layers", color=INK2, fontsize=10.5, va="center", alpha=ha)
        for i, name in enumerate(names):
            px = 192 + i * 66
            act = clamp(1 - abs(s - i))       # 1 while this is the current stage
            past = clamp(s - i)               # 1 once the morph has moved beyond it
            ov.add_patch(FancyBboxPatch((px, 250), 58, 21, boxstyle="round,pad=0,rounding_size=10.5",
                                        fc=mix(SURFACE, BLUE, act), ec=mix(mix(GRID, LIGHT_BLUE, past), BLUE, act),
                                        lw=1, alpha=ha))
            ov.text(px + 29, 260.5, name, ha="center", va="center", fontsize=9.5, alpha=ha,
                    color=mix(mix(MUTED, BLUE, past), "white", act), fontweight="bold" if act > 0.5 else "normal")

        # IM-free readout.
        rx = W - 46
        ov.text(rx, 292, "IM-free share", color=INK2, ha="right", va="center", fontsize=10.5, alpha=ha)
        ov.text(rx, 326, pct(share), color=BLUE, ha="right", va="center", fontsize=28, fontweight="bold", alpha=ha)
        ov.text(rx, 358, f"random pick: {pct(d['random'][0])}", color=INK2, ha="right", va="center",
                fontsize=9.5, alpha=ha)
        end = ease(ramp(s, 2.6, 0.4))
        ratio = d["shares"][-1] / d["random"][0]
        ov.text(rx, 378, f"{d['shots']:,} shots: {ratio:.0f}× random", color=BLUE, ha="right",
                va="center", fontsize=9.5, fontweight="bold", alpha=ha * end)
        footer_legend(fig, [Patch(color=BLUE, label="QAOA (Dicke start, XY mixer)"),
                            Patch(color=MUTED, label="Random pick")])


# ---------------------------------------------------------------------------
# Scene 3: the result

S3_LEN = 5.8
S3_GLIDE = (0.8, 1.6)


def scene_result(fig, d, t):
    ov = new_frame(fig)
    header(ov, 2, [(0, "QAOA's plan: three mics move, and their ghosts move too."),
                   (S3_GLIDE[0] + S3_GLIDE[1] + 0.1, "Zero ghost hits, checked product by product.")], t)
    a, b = np.array(d["newcomer"], float), np.array(d["plan"], float)
    g = ease(ramp(t, *S3_GLIDE))
    f = list(a + (b - a) * g)
    prods, hits = [], 0
    for v, src in third_order(f):
        vic = victims(f, v, src, d["guard"])
        hits += len(vic)
        prods.append((v, 1.0, 1.0 if vic else 0.0))
    spectrum(fig, d, f, [1.0] * len(f), prods, show_grid=True, mic_text=[1.0] * len(f))
    done = ramp(t, S3_GLIDE[0] + S3_GLIDE[1] - 0.05, 0.2)
    hit_counter(ov, hits, 1.0, [("evenly spaced plan", 1 - ramp(t, S3_GLIDE[0], 0.3)),
                                ("QAOA plan", ramp(t, S3_GLIDE[0] + S3_GLIDE[1], 0.3))], ok=done)
    footer_legend(fig, SPECTRUM_LEGEND)


# ---------------------------------------------------------------------------
# Timeline and GIF

SCENES = [(scene_problem, S1_LEN), (scene_quantum, S2_LEN), (scene_result, S3_LEN)]


def render(fig, scene, d, t):
    scene(fig, d, t)
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()


def frame_at(fig, d, t):
    """One frame at global time t. Neighbouring scenes overlap by FADE and crossfade.
    The last scene fades into the first frame of scene 1, so the loop is seamless."""
    start = 0.0
    for i, (scene, length) in enumerate(SCENES):
        if t < start + length:
            local = t - start
            img = render(fig, scene, d, local)
            if local > length - FADE:
                nxt, nt = (SCENES[i + 1][0], 0.0) if i + 1 < len(SCENES) else (SCENES[0][0], 0.0)
                w = ease((local - (length - FADE)) / FADE)
                img = (img * (1 - w) + render(fig, nxt, d, nt) * w).round().astype(np.uint8)
            return img
        start += length - FADE
    raise ValueError(t)


def duration():
    return sum(length for _, length in SCENES) - FADE * (len(SCENES) - 1)


def main():
    print("Running plan_mics for the numbers (about 20 s)...")
    d = gather()
    print(f"IM-free share by stage: {', '.join(pct(s) for s in d['shares'])}; plan {[f / 1e6 for f in d['plan']]}")
    plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans"})
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=SURFACE)
    # The first frame of scene 1 is also where the loop lands, so render it with the rest.
    n = int(round(duration() * FPS))
    frames = []
    for k in range(n):
        frames.append(frame_at(fig, d, k / FPS))
        if k % 40 == 0:
            print(f"  frame {k}/{n}")
    plt.close(fig)

    # One shared palette for every frame, so colours never flicker between frames.
    sample = np.concatenate(frames[::6], axis=0)
    palette = Image.fromarray(sample).quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    images = [Image.fromarray(fr).quantize(palette=palette, dither=Image.Dither.NONE) for fr in frames]
    images[0].save(OUT, save_all=True, append_images=images[1:], duration=int(1000 / FPS), loop=0,
                   optimize=False, disposal=1)
    print(f"Saved {os.path.relpath(OUT, ROOT)}: {n} frames, {duration():.1f} s, "
          f"{os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
