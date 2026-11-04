# Explainer 3: tuning, sampling, baselines and how to read the results

**Role:** [Member 3]. You own the tuning and sampling parts of `micplanner/quantum.py`, plus `micplanner/baselines.py`, `micplanner/plots.py` and `tools/make_figures.py`.

## What this part does

It picks good QAOA angles, runs the real Qiskit circuit, counts how often the samples are IM-free, and compares that with classical methods. It also makes the figures.

## The fast path (and why it is not cheating)

- Simulating the full 16-qubit circuit once takes about 15 seconds. Tuning needs thousands of evaluations, so that is too slow.
- The **fast path** simulates the same circuit exactly in NumPy, but only on the 4,368 five-mic plans. That is enough because the circuit never leaves those plans.
  - The cost layer multiplies each plan by a phase, exp(-i gamma C).
  - The mixer moves amplitude between plans that differ by one mic hopping to a neighbouring frequency, pair by pair, in the same even-then-odd order as the circuit.
- One evaluation takes well under a millisecond. Nothing is approximated.
- **Check:** at the final angles, the real Qiskit circuit (12,716 CNOTs, run as a `Statevector`) matches the fast path with fidelity 1.000000000000 and a leak outside the 5-mic plans of about 1e-13.
- We say this openly in the notebook. It works only because the demo is small. At large sizes you can't simulate classically, so you'd tune on hardware or with other tricks.

## Tuning

- Optimizer: SciPy's COBYLA. Seed 7 everywhere.
- p = 1: scan a 48 by 48 grid of (gamma, beta), then refine the best point.
- p = 2 and up: stretch the previous best angles to one more layer by interpolation (following Zhou et al.), plus six seeded random starts. Keep the best.
- Two objectives:
  - **Mean:** the average cost <C>.
  - **CVaR (alpha = 0.1):** the average cost of the best 10% of outcomes. It cares about the good tail, which is what we want: we only need one clean plan.

| Layers p | Mean objective | CVaR objective |
|---|---|---|
| 1 | 1.75% | 1.85% |
| 2 | 3.35% | 4.03% |
| 3 | 3.87% | **6.96%** |
| 4 | not run | 10.00% |
| 5 | not run | 12.12% |

(Chance that a sample is IM-free, exact, from the fast path. Uniform random is 0.55%.)

- CVaR wins, so `plan_mics` uses CVaR with p = 3. Alpha 0.1, 0.15 and 0.25 all reached the same p = 3 result.
- p = 4 and 5 ran only on the fast path, to keep the notebook quick. Always say so if you quote 12%.

## Sampling

- The final angles run on the real circuit through `StatevectorSampler`: 8,000 shots, seed 2026.
- **7.1% of samples are IM-free** (569 of 8,000). The exact value is 6.96%. The statistical spread for 8,000 shots is about 0.3 points, so they agree.
- Random plans are IM-free 0.55% of the time, so QAOA is about **13 times better than random**.
- The most common clean plan is 470.000, 470.500, 471.500, 472.750, 473.500 MHz, at 0.5% of shots. There are 24 clean plans, all tied at cost 0, so no single plan dominates. `plan_mics` returns the most common clean one.
- Exclusion run (13 qubits): 10.8% IM-free against 0.62% random.

## Classical baselines

| Method | Result on the demo | Time |
|---|---|---|
| Brute force | all 4,368 plans, 24 clean | about 10 ms |
| Greedy (add the frequency with the fewest new conflicts) | finds {470.00, 470.50, 471.25, 472.25, 473.75}, clean | about 1 ms |
| Greedy from each of the 16 starting points | 8 of 16 end clean | |
| Simulated annealing (swap moves keep 5 mics) | 50 of 50 runs end clean | about 0.06 s |
| Uniform random, 8,000 plans | 0.50% clean | |
| Integer program (SciPy `milp`) | optimal, clean | about 0.1 s |

**Say plainly: every classical method solves this instance at once.** QAOA does not beat them, and we never claim it does.

## How to read the figures

- **Histogram** (`fig_histogram.png`): the x-axis is the number of conflicting sets in a plan (0 means IM-free). Blue is QAOA samples, grey is all 4,368 plans weighted equally. QAOA moves weight toward 0 and 1 conflicts.
- **Layers chart** (`fig_clean_vs_p.png`): chance of an IM-free sample against p for both objectives, with the random line. The square marks what the circuit sampler measured at p = 3.
- **Convergence** (`fig_convergence.png`): best CVaR value so far against COBYLA evaluations, for the best start at each p.
- **Newcomer vs QAOA** (`fig_newcomer_vs_qaoa.png`): the evenly spaced plan has 20 hits (red crosses). The QAOA plan has none.

## Where the code lives

| What | Where |
|---|---|
| Fast path | `quantum.FastQAOA` |
| Tuning | `quantum.tune`, `quantum.landscape_p1` |
| Circuit check | `quantum.compare_with_circuit` |
| Sampling | `quantum.sample` |
| Baselines | `baselines.py` |
| Figures | `plots.py`, `tools/make_figures.py` (writes `figures/numbers.json`) |

## Likely questions

**You tuned on a classical computer. Isn't that cheating?** It is standard practice to tune small QAOA circuits by simulation, and we disclose it. The tuned angles then run on the real circuit, and the results match. It wouldn't scale, and we say so.

**7% sounds low. Is QAOA bad here?** It is 13 times better than random, but every classical method finds a clean plan instantly. QAOA is a heuristic, and our point is the modelling, not the score.

**Why does the mean objective stall near 4%?** The average rewards making bad plans slightly less bad. CVaR rewards the best tail, which is where clean plans live.

**Why COBYLA?** It needs no gradients, handles a handful of angles well, and is in SciPy.

**Are the numbers reproducible?** Yes. Seeds are fixed (tuning 7, sampling 2026), and the notebook recomputes everything when you run it.
