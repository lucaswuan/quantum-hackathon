"""Write mic_planner.ipynb from the cells below (without outputs), with micplanner/*.py embedded.

Run from the project folder: python tools/build_notebook.py
Then run and save it as a judge would: python tools/run_standalone.py
"""

import os

import nbformat as nbf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip("\n")))


def embedded_module(name):
    """A collapsed cell that writes micplanner/<name> from the source file, unchanged."""
    with open(os.path.join(ROOT, "micplanner", name), encoding="utf-8") as fh:
        source = fh.read()
    cell = nbf.v4.new_code_cell(f"%%writefile micplanner_embedded/micplanner/{name}\n{source}")
    cell.metadata["jupyter"] = {"source_hidden": True, "outputs_hidden": True}
    cells.append(cell)


md(r"""
# IM-free wireless mic planner

**[Team name]**: [Member 1], [Member 2], [Member 3], [Member 4]
Qiskit Fall Fest 2026, University of Waterloo

Wireless mics fail in a way that surprises newcomers. When several mics transmit at once, their signals mix and create ghost signals at new frequencies. If a ghost lands on another mic's frequency, that mic crackles. Professionals plan around this with vendor software or a dedicated RF coordinator. This notebook turns the planning rules into a cost function on qubits and searches it with QAOA, behind one plain-English function:

```python
plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz", im_guard="250 kHz")
```

The person using it never sees a QUBO, a Hamiltonian, a penalty weight or a mixer.

**What this is not.** QAOA is a heuristic. The demo has 4,368 possible plans, and brute force solves it in about 10 ms. We claim no speed-up. Our point is modelling: the intermodulation rules are three- and four-way interactions, QAOA takes them as they are, and the circuit itself keeps the mic count fixed.

**How to run.** Open this one file in Python 3.10 or newer and use Run all. The notebook carries its own code, and the Setup section installs any missing packages. Everything runs live on Qiskit's statevector simulator, in about two minutes on our laptop. Nothing is precomputed or loaded from a file.
""")

md(r"""
## Setup

This notebook is one self-contained file. The cells in this section run first.

1. The next cell checks for the Python packages and installs any that are missing.
2. The collapsed cells after it write the `micplanner` package, about 1,100 lines of plain Python, into a folder called `micplanner_embedded` next to this notebook.

To read the code, click the `...` bar of a collapsed cell. If your viewer shows those cells expanded, scroll down to section 1.
""")

code(r"""
import importlib, os, sys, time
from importlib.metadata import PackageNotFoundError, version

T0 = time.perf_counter()
TESTED_QISKIT = "2.6.1"
MINIMUM_QISKIT = (2, 1)


def packages_missing():
    try:
        for package in ("numpy", "scipy", "matplotlib"):
            version(package)
        return tuple(int(part) for part in version("qiskit").split(".")[:2]) < MINIMUM_QISKIT
    except PackageNotFoundError:
        return True


if packages_missing():
    %pip install -q "qiskit==2.6.1" numpy scipy matplotlib
    importlib.invalidate_caches()

print("Qiskit", version("qiskit"), "| SciPy", version("scipy"), "| Matplotlib", version("matplotlib"))
if version("qiskit") != TESTED_QISKIT:
    print(f"The numbers in the text come from Qiskit {TESTED_QISKIT}, so gate counts may differ slightly here.")

os.makedirs("micplanner_embedded/micplanner", exist_ok=True)
sys.path.append(os.path.abspath("micplanner_embedded"))
""")

for module in ("__init__.py", "engine.py", "cost.py", "quantum.py", "baselines.py", "plots.py", "api.py"):
    embedded_module(module)

md(r"""
Now import it. If a `micplanner` folder already sits next to the notebook, as it does in the project's repo, Python uses that one, and the embedded copy is only a fallback.
""")

code(r"""
import platform

import numpy as np
import matplotlib.pyplot as plt
import qiskit
from IPython.display import Markdown, display

import micplanner
from micplanner import plan_mics, engine, cost, quantum, baselines, plots

print("Python", platform.python_version(), "| Qiskit", qiskit.__version__, "| NumPy", np.__version__)
print("Code loaded from", os.path.relpath(os.path.dirname(micplanner.__file__)))
""")

md(r"""
## 1. The problem in plain words

Every wireless mic transmits on its own carrier frequency. Radio electronics are slightly non-linear, so two carriers $f_1$ and $f_2$ mix and create third-order intermodulation (IM) products at

$$2f_1 - f_2 \qquad \text{and} \qquad 2f_2 - f_1 .$$

Three carriers also create three-tone products such as $f_1 + f_2 - f_3$. These products are weak, but a receiver tuned to the same frequency hears them as noise. Shure's guide notes that "most manufacturers recommend" at least 250 kHz between any third-order product and any carrier [1].

A worked example with two mics:
""")

code(r"""
f1, f2 = 470.50, 471.25
print(f"2 x f1 - f2 = {2 * f1 - f2:.2f} MHz")
print(f"2 x f2 - f1 = {2 * f2 - f1:.2f} MHz")
plots.plot_ghost_example();
""")

md(r"""
The count grows fast. $n$ carriers make $n(n-1)$ two-tone and $\binom{n}{2}(n-2)$ three-tone third-order products. Shure's page says three transmitters "may generate six in-band 3rd order" products [1]. Our formula gives nine for three carriers because it counts every two-tone and three-tone product wherever it lands, so the two counts measure different things.
""")

code(r"""
for n in (3, 5, 10, 40):
    c = engine.count_third_order_products(n)
    print(f"{n:>2} mics: {c['two-tone']:>6,} two-tone + {c['three-tone']:>6,} three-tone = {c['total']:>6,}")
""")

md(r"""
## 2. Using the tool

**The story.** The Humanities Theatre in Hagey Hall at the University of Waterloo seats up to 721 people [3]. Its technical specifications list three Shure ULD handheld microphones and three Shure ULD wireless body-pack transmitters [4]. Suppose a show uses five of those six Shure channels at once.

The venue pages give no frequency bands or receiver models. So the band below, 470 to 474 MHz, is illustrative, and so is the exclusion further down. A real plan needs the receivers' actual tuning range and a check of local TV channels.

**The rules.** Carriers at least 500 kHz apart (our demo choice, not a vendor rule) and no third-order product within 250 kHz of any carrier [1]. The tool lays a 250 kHz grid over the band. The top edge is left out, so that gives 16 frequencies, which means 16 qubits.
""")

code(r"""
plan = plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz",
                 im_guard="250 kHz", csv_path="outputs/plan_humanities_theatre.csv")
""")

md(r"""
The plan is saved as a CSV file that a sound tech can open in a spreadsheet:
""")

code(r"""
print(open(plan.csv_path).read())
""")

md(r"""
Now suppose 472.0 to 472.5 MHz is already in use by something else in the building (an illustrative exclusion). One extra argument handles it. Three grid points drop out, so this run uses 13 qubits.
""")

code(r"""
plan_x = plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz", im_guard="250 kHz",
                   exclude=["472.0-472.5 MHz"], csv_path="outputs/plan_with_exclusion.csv")
""")

md(r"""
## 3. How it works

**The rules become a cost function.** Each allowed frequency $k$ gets a bit $x_k$, which is 1 when a mic sits there. There are three kinds of conflict:

- $P$: pairs of frequencies closer than the carrier spacing.
- $T$: triples where a two-tone product $2f_k - f_l$ lands within the IM guard of a third mic $f_m$.
- $Q$: quadruples where a three-tone product $f_k + f_l - f_p$ lands within the IM guard of a fourth mic $f_m$.

Each conflicting set counts once:

$$C(x) = \sum_{(k,l)\in P} x_k x_l \;+\; w_3 \sum_{(k,l,m)\in T} x_k x_l x_m \;+\; w_3 \sum_{(k,l,p,m)\in Q} x_k x_l x_p x_m, \qquad \sum_k x_k = n, \qquad w_3 = 1 .$$

A plan is IM-free exactly when $C(x) = 0$, and any $w_3 > 0$ gives the same clean plans.

**The cost becomes qubits.** Substituting $x_k = (1 - Z_k)/2$ turns $C$ into a sum of Pauli-Z strings with up to four $Z$'s,

$$H_C = \sum_{S} c_S \prod_{k \in S} Z_k ,$$

which is diagonal, with $C(x)$ on the diagonal. Qiskit holds it as a `SparsePauliOp`.

**The circuit keeps the mic count.** QAOA prepares

$$|\psi(\boldsymbol\gamma, \boldsymbol\beta)\rangle = U_M(\beta_p)\, e^{-i\gamma_p H_C} \cdots U_M(\beta_1)\, e^{-i\gamma_1 H_C}\, |D^N_n\rangle .$$

- The start is the Dicke state $|D^N_n\rangle = \binom{N}{n}^{-1/2} \sum_{|x| = n} |x\rangle$: every $n$-mic plan with equal weight. We build it with the deterministic circuit of Bärtschi and Eidenbenz [8].
- The mixer is $U_M(\beta) = e^{-i\beta H_{\mathrm{odd}}}\, e^{-i\beta H_{\mathrm{even}}}$, where $H_{\mathrm{even}} = \tfrac12 \sum_{k\ \mathrm{even}} (X_k X_{k+1} + Y_k Y_{k+1})$ and $H_{\mathrm{odd}}$ is the same sum over the odd pairs plus the pair that closes the ring [9, 10]. Each $XX + YY$ term only swaps $|01\rangle$ and $|10\rangle$. It moves a mic to a neighbouring frequency and never adds or removes one.
- This product is not exactly $e^{-i\beta H_{XY}}$, because neighbouring pairs do not commute. It is what the circuit does, and our fast simulation uses the same product.
- So every sample has exactly $n$ mics, with no penalty weight to tune. The circuit is built with Qiskit's `qaoa_ansatz` function. The `QAOAAnsatz` class is deprecated in Qiskit 2.x.

**An honest note.** On this grid the guard means "lands exactly on a mic", and the spacing rule forbids neighbouring points. So an IM-free plan is a set whose pairwise differences are all distinct and never 1: a Golomb ruler (a Sidon set) with no gap of 1. The link between IM-free channels and these rulers goes back to Babcock in 1953 [14]. The engine handles any guard, step and exclusion, but this demo instance is that classic puzzle.
""")

code(r"""
inst = plan.instance
print(inst.describe())
H_C = cost.cost_operator(inst)
zs = cost.z_strings_by_weight(H_C)
print("Z-strings by weight:", zs, "| total:", sum(zs.values()))
""")

md(r"""
The pieces at a size small enough to print: the Dicke circuit for two mics on four frequencies, and the XY mixer's terms in the order Qiskit synthesizes them.
""")

code(r"""
print(quantum.dicke_circuit(4, 2).draw("text"))
print(quantum.xy_mixer_operator(4))
""")

md(r"""
## 4. Checks

**The cost operator matches the classical cost.** At 12 qubits every basis state is checked with Qiskit's own matrix. At 16 qubits, 32 random basis states are checked with `Statevector` expectation values, and all 65,536 by a direct parity sum.
""")

code(r"""
small = engine.build_instance("470-473 MHz", mics=4)
print(f"{small.n_points} qubits:", cost.check_diagonal(small, cost.cost_operator(small)))
print("16 qubits:", cost.check_diagonal(inst, H_C, n_spot=32))
""")

md(r"""
**The mixer never changes the mic count**, and Qiskit's synthesis of the mixer is exactly the even-then-odd product (checked on 6 qubits against explicit `RXX` and `RYY` gates).
""")

code(r"""
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import Operator, SparsePauliOp, Statevector

n = 6
qc = QuantumCircuit(n)
qc.append(PauliEvolutionGate(quantum.xy_mixer_operator(n), time=0.41), range(n))
U = Operator(transpile(qc, basis_gates=quantum.BASIS, optimization_level=1)).data
weight = np.array([bin(i).count("1") for i in range(2 ** n)])
print("largest amplitude that changes the mic count:", np.abs(U[weight[:, None] != weight[None, :]]).max())
V = Operator(quantum.xy_mixer_circuit(n, 0.41)).data
print("synthesized mixer equals the even-then-odd product:", np.allclose(U, U[0, 0] / V[0, 0] * V))
""")

md(r"""
**The Dicke circuit makes the right state.**
""")

code(r"""
dk = transpile(quantum.dicke_circuit(16, 5), basis_gates=quantum.BASIS, optimization_level=1)
fid = abs(np.vdot(quantum.dicke_vector(16, 5), Statevector(dk).data)) ** 2
print(f"Dicke(16, 5): fidelity {fid:.12f} with the exact state, {dk.count_ops()['cx']} CNOTs")
""")

md(r"""
**Through the Estimator primitive.** On an 8-frequency, 3-mic instance, `StatevectorEstimator` gives the circuit's $\langle C \rangle$, which must match the fast simulation, and the mic-count operator $N = \sum_k (1 - Z_k)/2$, which must have no spread at all.
""")

code(r"""
from qiskit.primitives import StatevectorEstimator

s8 = engine.build_instance("470-472 MHz", mics=3)
fast8 = quantum.FastQAOA(s8)
g, b = [0.6, 0.9], [0.4, 0.3]
circ8 = quantum.compile_ansatz(quantum.build_ansatz(cost.cost_operator(s8), 3, reps=2))
bound8 = circ8.assign_parameters(quantum.angle_binding(circ8, g, b))
N_op = SparsePauliOp.from_sparse_list([("", [], s8.n_points / 2)] + [("Z", [k], -0.5) for k in range(s8.n_points)],
                                      s8.n_points)
evs = StatevectorEstimator().run([(bound8, [cost.cost_operator(s8), N_op, (N_op @ N_op).simplify()])]).result()[0].data.evs
print(f"<C>: circuit {evs[0]:.10f}, fast path {fast8.expectation(fast8.probs(g, b)):.10f}")
print(f"<N> = {evs[1]:.6f}, variance of N = {abs(evs[2] - evs[1] ** 2):.1e} (zero up to rounding)")
""")

md(r"""
## 5. Running QAOA

**Disclosure: angles are tuned on an exact NumPy simulation, then confirmed on the real circuit.** The cost layer is a diagonal phase, and the mixer acts pair by pair on the 4,368 five-mic plans, in the same order as the circuit. One evaluation takes well under a millisecond, against about 15 seconds for one statevector run of the full circuit. Nothing is approximated.

Two objectives are tried: the plain expectation $\langle C\rangle$, and CVaR with $\alpha = 0.1$, the mean cost of the best 10% of outcomes [11]. COBYLA tunes the angles layer by layer: a grid scan for $p = 1$, then the previous optimum stretched to $p + 1$ layers by interpolation, following Zhou et al. [12], plus six seeded random starts.
""")

code(r"""
fast = quantum.FastQAOA(inst)
mean_res = quantum.tune(fast, max_p=3, kind="mean")
cvar_res = quantum.tune(fast, max_p=5, kind="cvar", alpha=0.1)
for name, rs in (("mean", mean_res), ("CVaR", cvar_res)):
    for r in rs:
        print(f"{name:>4}, p = {r.p}: IM-free probability {r.clean_prob:6.2%}, <C> = {r.expected_cost:.3f}")
print(f"uniform random: {fast.clean.mean():.2%}")
""")

code(r"""
plots.plot_convergence(cvar_res[:3], "COBYLA convergence, CVaR objective");
""")

code(r"""
plots.plot_clean_vs_p({"Mean of C": mean_res, "CVaR, alpha 0.1": cvar_res}, fast.clean.mean(),
                      sampled=(3, plan.clean_share));
""")

md(r"""
CVaR gives more IM-free samples, so `plan_mics` uses it with $p = 3$. Layers 4 and 5 ran only on the fast simulation, to keep this notebook quick. The mean objective stalls near 4%. The $p = 3$ CVaR angles here are the same ones `plan_mics` used in section 2, because both runs use the same seed:
""")

code(r"""
best = cvar_res[2]
print("same angles as plan_mics:", np.allclose(best.gammas, plan.tuning[-1].gammas)
      and np.allclose(best.betas, plan.tuning[-1].betas))
print("gamma =", np.round(best.gammas, 4), " beta =", np.round(best.betas, 4))
""")

md(r"""
**The real circuit at those angles.** `qaoa_ansatz` with the Dicke start and XY mixer, transpiled to `cx, rz, sx, x`, run as a Qiskit `Statevector` and compared with the fast simulation.
""")

code(r"""
circ = quantum.compile_ansatz(quantum.build_ansatz(H_C, 5, reps=3))
agree = quantum.compare_with_circuit(fast, circ, best.gammas, best.betas)
print(f"fidelity {agree['fidelity']:.12f}")
print(f"probability outside the 5-mic plans {agree['leakage']:.1e}")
print(f"largest probability difference {agree['max_prob_diff']:.1e}  ({agree['seconds']:.0f} s for the statevector run)")
""")

md(r"""
**The samples.** `plan_mics` drew 8,000 shots from `StatevectorSampler`. The most common ones:
""")

code(r"""
top = sorted(plan.counts.items(), key=lambda kv: -kv[1])[:8]
for m, c in top:
    idx = engine.mask_to_indices(m)
    print(f"{c:4d} shots  {', '.join(f'{inst.freqs[i] / 1e6:.2f}' for i in idx)} MHz  "
          f"conflicting sets: {engine.cost_of(inst, idx):.0f}")
print(f"\nIM-free samples: {plan.clean_share:.2%} (exact {best.clean_prob:.2%}), uniform random {plan.random_share:.2%}")
""")

md(r"""
## 6. Results against classical baselines

Every classical method below solves this instance at once. That is expected with 16 frequencies.
""")

code(r"""
rows = [baselines.run_brute_force(inst), baselines.greedy(inst), baselines.simulated_annealing(inst)["result"],
        baselines.uniform_random(inst)["result"], baselines.milp_solve(inst)]
clean_starts, _ = baselines.greedy_all_starts(inst)
fmt = lambda idx: ", ".join(f"{inst.freqs[i] / 1e6:.2f}" for i in idx)
table = ["| Method | Plan (MHz) | IM-free | Time | Note |", "|---|---|---|---|---|"]
for r in rows:
    table.append(f"| {r.name} | {fmt(r.plan)} | {'yes' if r.clean else 'no'} | {r.seconds * 1e3:.1f} ms | {r.note} |")
table.append(f"| QAOA, p = 3, CVaR (this work) | {fmt(plan.plan_indices)} | {'yes' if plan.clean else 'no'} | "
             f"{plan.seconds['total']:.0f} s | {plan.clean_share:.1%} of 8,000 samples IM-free |")
display(Markdown("\n".join(table)))
print(f"Greedy from each of the {inst.n_points} starting points ends clean {clean_starts} times.")
""")

md(r"""
**QAOA against random.** The histogram compares the QAOA samples with the exact spread over all 4,368 plans, which is what the Dicke start alone would give.
""")

code(r"""
q_costs = [engine.cost_of(inst, engine.mask_to_indices(m)) for m in plan.counts]
q_w = np.array(list(plan.counts.values())) / plan.shots
plots.plot_histogram(q_costs, q_w, fast.cost, np.full(fast.dim, 1 / fast.dim),
                     labels=("QAOA, 8,000 samples", "Uniform random, all 4,368 plans"));
""")

md(r"""
**What a newcomer might do.** Greedy is not our bad example, because greedy solves this instance (see the table). A person without software might instead space the mics evenly. That is the worst case: evenly spaced carriers are full of arithmetic progressions, and every progression puts a product right on a mic. The checker lists each hit.
""")

code(r"""
newcomer = (0, 3, 6, 9, 12)
nc = engine.check_indices(inst, newcomer)
print(nc.report())
hz = lambda idx: [inst.freqs[i] for i in idx]
plots.plot_side_by_side((hz(newcomer), f"Evenly spaced, as a newcomer might pick: {len(nc.violations)} hits"),
                        (hz(plan.plan_indices), "QAOA plan: no hits"), inst.spacing, inst.im_guard,
                        band=inst.band, grid=inst.freqs);
""")

md(r"""
## 7. Resource card

Gate counts after transpiling to `cx, rz, sx, x` (optimization level 1, all-to-all connectivity), and the size of the same problem written as a QUBO.
""")

code(r"""
card = quantum.resource_card(H_C, n_mics=5, reps=3)
qs = cost.qubo_size(inst)
zs = card["z_strings"]
rows = [("Qubits", f"{card['qubits']}"),
        ("Z-strings by weight 1 / 2 / 3 / 4", " / ".join(str(zs[w]) for w in (1, 2, 3, 4)) + f" ({sum(zs.values())} in all)"),
        ("Dicke start", f"{card['dicke']['cx']:,} CNOTs"),
        ("One cost layer, as built by qaoa_ansatz", f"{card['cost_layer']['cx']:,} CNOTs "
         f"(naive ladder count {card['cost_layer_naive_cx']:,}; {card['cost_layer_single_gate']['cx']:,} "
         "if synthesized as one PauliEvolutionGate)"),
        ("One XY mixer layer", f"{card['mixer_layer']['cx']} CNOTs"),
        ("Full circuit, p = 3", f"{card['full']['cx']:,} CNOTs, depth {card['full']['depth']:,}"),
        ("Transpile time, full circuit", f"{card['full']['transpile_s']:.2f} s"),
        ("Statevector run, full circuit", f"{agree['seconds']:.0f} s"),
        ("Same problem as a QUBO", f"{qs['variables']} binary variables (greedy Rosenberg; "
         f"{qs['best_variables']} to {qs['worst_variables']} over {qs['trials']} tie-break orders)")]
display(Markdown("| Item | Value |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows)))
print(f"{qs['qubits']} qubits here vs {qs['variables']} variables as a QUBO")
""")

md(r"""
**Why the QUBO is bigger.** A QUBO allows only pairs of variables. Each triple or quadruple term needs auxiliary variables $y = x_i x_j$, held in place by Rosenberg penalty terms [13]. We count them greedily: replace the pair that appears in the most high-degree terms, and repeat until every term has two variables or fewer. A QUBO would also need a penalty to hold the mic count at 5.

**The other side of the trade.** The gate model pays in depth instead: about 4,000 CNOTs per cost layer and 12,716 for the whole $p = 3$ circuit. We have not run it on hardware, and we expect a circuit this deep to be dominated by noise on current devices.
""")

md(r"""
## 8. Where it falls short

- **No speed-up.** QAOA is a heuristic with no proven advantage here, and we claim none.
- **Classically trivial at this size.** Brute force takes about 10 ms. Greedy solves it, and simulated annealing ends clean in 50 of 50 runs.
- **A modest gain over random.** At $p = 3$, 7.1% of samples are IM-free against 0.55% for random plans, about 13 times better. On the fast simulation, $p = 5$ reaches 12%. The angles were tuned by exact classical simulation, which is impossible at large sizes.
- **It is a Golomb-ruler search here.** With exact landings on a uniform grid, IM-free plans are Golomb rulers with no gap of 1, a connection known since 1953 [14].
- **A guard model simpler than a coordinator's.** Third-order products only (Shure also lists fifth-order ones [1]). No TV channel data, transmitter power, distance or receiver selectivity. A uniform grid, and every carrier treated alike.
- **Venue facts.** The band and the exclusion are illustrative, not the theatre's real setup.
- **Free vendor tools exist.** Shure's Wireless Workbench is free [15] and far more complete. Our contribution is a quantum route that models IM, behind a plain-English interface, not a replacement for those tools.

**Beyond the toy size.** Six IM-free mics with these rules need 21 grid points, and only two plans work:
""")

code(r"""
six = engine.build_instance("470-475.25 MHz", mics=6)
bf6 = engine.brute_force(six)
print(f"6 mics: {six.n_points} points ({six.n_points} qubits), {bf6.n_plans:,} plans, {bf6.n_clean} IM-free:",
      [[f"{six.freqs[i] / 1e6:.2f}" for i in p] for p in bf6.best_plans])
""")

md(r"""
For 40 mics on this kind of grid, the 780 pairwise differences must be distinct and at least 2, so the largest is at least 781. The grid then needs at least 782 points, which is 782 qubits and about 195 MHz at 250 kHz steps. The number of conflicting sets on such a grid:
""")

code(r"""
N40 = 782
T40, Q40 = engine.uniform_grid_term_counts(N40)
print(f"{N40} qubits: {T40:,} triple terms and {Q40:,} quadruple terms")
print(f"for comparison, 16 points: {engine.uniform_grid_term_counts(16)}")
""")

md(r"""
That is tens of millions of four-body terms in every cost layer. A real system would also work off-grid, with finer tuning steps and several bands. A practical quantum route at that size would need a much sparser model, problem decomposition, or both. That is open work.
""")

md(r"""
## 9. References

1. Shure, "All about wireless intermodulation distortion". https://www.shure.com/en-US/insights/all-about-wireless-intermodulation-distortion
2. SoundPro, "RF coordination for live events" (2026 guide). https://soundpro.com/blogs/live-production/rf-coordination-live-events-guide-2026
3. University of Waterloo Theatres, "Our theatres". https://uwaterloo.ca/theatres/venue-rental/our-theatres
4. University of Waterloo Theatres, "Humanities Theatre technical specs". https://uwaterloo.ca/theatres/venue-rental/humanities-theatre/humanities-theatre-technical-specs
5. D-Wave, frequency-selection example. https://github.com/dwave-examples/frequency-selection
6. M. Vandelli, F. Ferrari, D. Dragoni, "Constraint-preserving quantum algorithm for the multi-frequency antenna placement problem", arXiv:2511.15566 (2025).
7. E. Farhi, J. Goldstone, S. Gutmann, "A Quantum Approximate Optimization Algorithm", arXiv:1411.4028 (2014).
8. A. Bärtschi, S. Eidenbenz, "Deterministic Preparation of Dicke States", arXiv:1904.07358 (2019).
9. S. Hadfield et al., "From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz", Algorithms 12(2), 34 (2019), arXiv:1709.03489.
10. Z. Wang, N. C. Rubin, J. M. Dominy, E. G. Rieffel, "XY-mixers: analytical and numerical results for QAOA", Phys. Rev. A 101, 012320 (2020), arXiv:1904.09314.
11. P. Kl. Barkoutsos et al., "Improving Variational Quantum Optimization using CVaR", Quantum 4, 256 (2020), arXiv:1907.04769.
12. L. Zhou et al., "Quantum Approximate Optimization Algorithm: Performance, Mechanism, and Implementation on Near-Term Devices", Phys. Rev. X 10, 021067 (2020), arXiv:1812.01041.
13. I. G. Rosenberg, "Reduction of bivalent maximization to the quadratic case", Cahiers du Centre d'Études de Recherche Opérationnelle 17, 71 to 74 (1975).
14. W. C. Babcock, "Intermodulation Interference in Radio Systems", Bell System Technical Journal 32, 63 to 73 (1953), doi:10.1002/j.1538-7305.1953.tb01422.x.
15. Shure, "Wireless Workbench". https://shure.com/en-us/products/software/wwb
16. A. Javadi-Abhari et al., "Quantum computing with Qiskit", arXiv:2405.08810 (2024).
""")

code(r"""
print(f"Notebook runtime: {time.perf_counter() - T0:.0f} s")
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                  "language_info": {"name": "python"}}
path = os.path.join(ROOT, "mic_planner.ipynb")
nbf.write(nb, path)
print("wrote", path, "with", len(cells), "cells")
