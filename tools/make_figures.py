"""Build every PNG in figures/ and print the numbers the slides quote.

Run with the venv's Python from the project folder: python tools/make_figures.py
It repeats the notebook's computations with the same seeds, so the slides and the notebook agree.
"""

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from micplanner import baselines as B
from micplanner.api import plan_mics
from micplanner.cost import cost_operator, qubo_size, z_strings_by_weight
from micplanner.engine import brute_force, build_instance, check_indices, cost_of, cost_vector, mask_to_indices
from micplanner.plots import (plot_clean_vs_p, plot_convergence, plot_ghost_example, plot_histogram,
                              plot_product_growth, plot_side_by_side, plot_spectrum)
from micplanner.quantum import FastQAOA, build_ansatz, compare_with_circuit, compile_ansatz, resource_card, tune


def save(fig, name, slide_variant=False):
    """Save the figure. With slide_variant, also save a copy without the chart title, since the slide has one."""
    fig.savefig(f"figures/{name}.png", dpi=200, bbox_inches="tight")
    if slide_variant:
        for ax in fig.axes:
            for loc in ("left", "center", "right"):
                ax.set_title("", loc=loc)
        fig.savefig(f"figures/{name}_slide.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_cost_equation():
    """The slide's cost function, typeset by Matplotlib: white on transparent, for the dark bar on slide 5."""
    equation = (r"$C(x)=\sum_{(k,l)\in P}x_kx_l+\sum_{(k,l,m)\in T}x_kx_lx_m"
                r"+\sum_{(k,l,p,m)\in Q}x_kx_lx_px_m,\qquad\sum_kx_k=5$")
    with plt.rc_context({"mathtext.fontset": "cm"}):
        fig = plt.figure(figsize=(11, 1))
        fig.text(0.5, 0.5, equation, ha="center", va="center", fontsize=22, color="white")
        fig.savefig("figures/fig_cost_equation.png", dpi=300, bbox_inches="tight", pad_inches=0.02, transparent=True)
    plt.close(fig)


t_all = time.perf_counter()
numbers = {}

save_cost_equation()
save(plot_ghost_example(), "fig_ghost_example", slide_variant=True)
save(plot_product_growth(), "fig_product_growth", slide_variant=True)

story = plan_mics(csv_path="outputs/plan_humanities_theatre.csv",
                  title="Five Shure channels, 470 to 474 MHz (illustrative band)")
save(story.figure, "fig_plan_story")
excl = plan_mics(exclude=["472.0-472.5 MHz"], csv_path="outputs/plan_with_exclusion.csv",
                 title="Same band with 472.0 to 472.5 MHz kept clear (illustrative)")
save(excl.figure, "fig_plan_exclusion")

inst = story.instance
fast = FastQAOA(inst)
bf = brute_force(inst)
mean_res = tune(fast, max_p=3, kind="mean")
cvar_res = tune(fast, max_p=5, kind="cvar", alpha=0.1)
save(plot_convergence(cvar_res[:3], "COBYLA convergence, CVaR objective"), "fig_convergence")
save(plot_clean_vs_p({"Mean of C": mean_res, "CVaR, alpha 0.1": cvar_res}, bf.clean_share,
                     sampled=(3, story.clean_share)), "fig_clean_vs_p", slide_variant=True)

# Histogram: QAOA samples against the exact uniform distribution over all plans.
q_costs = np.array([cost_of(inst, mask_to_indices(m)) for m in story.counts])
q_w = np.array(list(story.counts.values())) / story.shots
r_costs = fast.cost
r_w = np.full(fast.dim, 1 / fast.dim)
save(plot_histogram(q_costs, q_w, r_costs, r_w, labels=("QAOA, 8,000 samples", "Uniform random, all 4,368 plans")),
     "fig_histogram", slide_variant=True)

# Red plan against the QAOA plan.
newcomer = (0, 3, 6, 9, 12)
nc = check_indices(inst, newcomer)
hz = lambda idx: [inst.freqs[i] for i in idx]
save(plot_side_by_side((hz(newcomer), f"Evenly spaced, as a newcomer might pick: {len(nc.violations)} hits"),
                       (hz(story.plan_indices), "QAOA plan: no hits"), inst.spacing, inst.im_guard,
                       band=inst.band, grid=inst.freqs), "fig_newcomer_vs_qaoa")
fig, ax = plt.subplots(figsize=(11, 3.4))
plot_spectrum(hz(newcomer), inst.spacing, inst.im_guard, ax=ax, band=inst.band, grid=inst.freqs,
              title=f"Evenly spaced plan: {len(nc.violations)} hits")
save(fig, "fig_newcomer_plan")

# Circuit check at the tuned p = 3 angles.
op = cost_operator(inst)
compiled = compile_ansatz(build_ansatz(op, 5, 3))
best = story.tuning[-1]
agree = compare_with_circuit(fast, compiled, best.gammas, best.betas)
card = resource_card(op, 5, 3)

greedy = B.greedy(inst)
g_clean, _ = B.greedy_all_starts(inst)
sa = B.simulated_annealing(inst)
rnd = B.uniform_random(inst)
mi = B.milp_solve(inst)
qs = qubo_size(inst)

six = build_instance("470-475.25 MHz", mics=6)
bf6 = brute_force(six)

numbers.update({
    "grid_points": inst.n_points, "plans": bf.n_plans, "spaced": bf.n_spaced, "clean": bf.n_clean,
    "clean_share": bf.clean_share, "clean_share_spaced": bf.clean_share_spaced, "brute_force_ms": bf.seconds * 1e3,
    "story_plan_mhz": story.plan_mhz, "story_clean_share": story.clean_share, "story_plan_share": story.plan_share,
    "story_seconds": story.seconds, "excl_points": excl.instance.n_points, "excl_plan_mhz": excl.plan_mhz,
    "excl_clean_share": excl.clean_share, "excl_random_share": excl.random_share,
    "mean_clean_by_p": [r.clean_prob for r in mean_res], "cvar_clean_by_p": [r.clean_prob for r in cvar_res],
    "cvar_p3_angles": {"gamma": list(best.gammas), "beta": list(best.betas)},
    "agreement": agree, "resource_card": card, "z_strings": z_strings_by_weight(op), "qubo": qs,
    "newcomer_counts": nc.counts, "newcomer_cost": cost_of(inst, newcomer),
    "greedy_plan": greedy.plan, "greedy_clean": greedy.clean, "greedy_starts_clean": g_clean,
    "sa_clean_runs": sa["clean_runs"], "sa_seconds": sa["result"].seconds, "random_share_8000": rnd["share"],
    "milp_plan": mi.plan, "milp_seconds": mi.seconds,
    "six_mic_points": six.n_points, "six_mic_plans": bf6.n_plans, "six_mic_clean": bf6.n_clean,
    "six_mic_best": bf6.best_plans if bf6.best_cost == 0 else [],
    "total_seconds": time.perf_counter() - t_all,
})
with open("figures/numbers.json", "w") as fh:
    json.dump(numbers, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(numbers, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
