# Final report: overnight build, November 3 to 4

Every deliverable in section 6 of the brief exists, and the final checks in section 7 pass. Nothing was blocked. The full decision log is in `PROGRESS.md`.

## What was built, and where

| Deliverable | Where | State |
|---|---|---|
| Notebook (the main deliverable) | `mic_planner.ipynb` | Title plus nine sections, saved with outputs. Runs top to bottom headless with no errors. |
| Package | `micplanner/` (`engine.py`, `cost.py`, `quantum.py`, `baselines.py`, `plots.py`, `api.py`) | `plan_mics(...)` works on the story and the exclusion case. |
| Tests | `tests/` | 35 passing (`.venv\Scripts\python -m pytest`). |
| Figures | `figures/*.png`, `figures/numbers.json` | Built by `tools/make_figures.py`. `numbers.json` holds every number the slides quote. |
| Slides | `slides/mic_planner_deck.pptx`, `slides/deck_outline.md` | 12 slides, 16:9, speaker notes on all. Render-checked in PowerPoint. |
| Team prep | `team/` | Four explainers (one per role), judge Q&A (23 questions), demo script, limitations. |
| README | `README.md` | Three-command run, folder map, how to rebuild. |
| Build scripts | `tools/` | Figures, notebook, slides, slide render, output viewer. Added beyond the brief's folder map. |
| CSV plans | `outputs/` | Written by `plan_mics`. Added beyond the brief's folder map. |
| Log | `PROGRESS.md` | One section per phase. |

Git: one commit per phase, pushed to https://github.com/lucaswuan/quantum-hackathon on November 4.

## Key numbers

**Instance.** 470 to 474 MHz (top edge excluded), 250 kHz steps: 16 frequencies, so 16 qubits. 5 mics, carriers at least 500 kHz apart (demo choice), no third-order product within 250 kHz of a mic (strictly less than, following Shure's "most manufacturers recommend" wording). Story: five of the Humanities Theatre's six Shure ULD channels. The band is illustrative.

**IM-free count.** 4,368 five-mic plans, 792 meeting the spacing rule, **24 IM-free** (0.55% of all plans, 3.0% of well-spaced ones). Matches the brief's expected check. Conflict sets: 15 pairs, 56 triples, 252 quadruples. 948 Z-strings (16, 120, 560, 252 by weight).

**QAOA against random.** At p = 3 with a CVaR objective (alpha 0.1), angles tuned on the exact fast path and run on the real circuit through `StatevectorSampler`:

- **7.1% of 8,000 samples are IM-free** (exact 6.96%), against **0.55% for uniform random**: about 13 times better.
- The plain mean objective reaches 3.87% at p = 3, so CVaR was kept, as the brief asks.
- On the fast path only: 10.0% at p = 4 and 12.1% at p = 5.
- Exclusion case (13 qubits): 10.8% against 0.62%.

**Best plan.** All 24 clean plans tie at cost 0, so there is no single best. `plan_mics` returns the most common clean sample: **470.000, 470.500, 471.500, 472.750, 473.500 MHz** (0.5% of shots). Brute force, greedy and the integer program return 470.00, 470.50, 471.25, 472.25, 473.75. Every classical baseline solves the demo at once. Greedy from each of the 16 starting points ends clean 8 times. Simulated annealing ends clean in 50 of 50 runs.

**Notebook runtime.** Headless `nbconvert --execute`: 81 s, 81 s, 116 s and 94 s wall-clock across the four full runs tonight (the in-notebook timer reads 77 to 109 s). The last run, on a copy that was then deleted, gave the same 7.11% and no errors. Under the 5-minute limit with room to spare.

**Qubits and two-qubit gates** (basis `cx, rz, sx, x`, transpile level 1, all-to-all):

| Piece | CNOTs |
|---|---|
| Dicke start, 16 qubits, 5 mics | 560 |
| One cost layer as `qaoa_ansatz` builds it | 4,006 (naive ladder count 3,992; 2,570 when built as one gate) |
| One XY mixer layer | 46 |
| Full circuit, p = 3 | **12,716**, depth 12,076 |

**QUBO comparison.** "16 qubits here vs 121 variables as a QUBO" (greedy Rosenberg substitution, 105 auxiliary variables). The range over 200 tie-break orders is 114 to 125. **The brief's earlier 89 did not reproduce**, and the brief's "about 5,700 CNOTs per cost layer" became 4,006.

## What is verified

- Cost operator: its diagonal equals the classical cost on every basis state at 12 qubits (Qiskit's matrix) and on all 65,536 at 16 qubits (direct parity, plus 32 states through `Statevector`). Max error 0.
- Dicke circuit: exact for every n up to 8 and every k. Fidelity 1.000000000000 for (16, 5) after transpiling.
- XY mixer: keeps the mic count exactly (leak about 1e-16). Qiskit's synthesis of the operator equals the even-then-odd product we write down.
- Fast path against the real circuit at the final p = 3 angles: fidelity 1.000000000000, leak about 1e-13. Sampled 7.1% against exact 6.96%, within shot noise.
- `StatevectorEstimator` on the 8-point instance: <C> matches the fast path to 10 digits, <N> = 3 with zero variance.
- Brute force reproduces the brief's 24 / 4,368 / 792. The inclusive 250 kHz reading gives 0 clean plans, as the brief said.
- Every reported plan is re-checked product by product with plain arithmetic.
- Sources re-opened tonight: Shure IMD page, both UW Theatres pages, SoundPro guide, D-Wave example, Vandelli et al. (arXiv abstract and HTML), Shure Wireless Workbench page (it is free), and the arXiv pages for Farhi, Hadfield, Wang, Bärtschi, Barkoutsos, Zhou and Javadi-Abhari.
- Slides: file validator passes. All 12 slides rendered through PowerPoint and inspected, with no overflow.

## What is not verified

- **No hardware run** (by design: simulator only).
- **Only tested on this laptop:** Windows, Python 3.14.8. Not tried on macOS, Linux or other Python versions. Judges' machines may be slower.
- **Babcock 1953** is cited from the reference list of Wikipedia's Golomb ruler article, not the paper itself. **Rosenberg 1975's** title comes from later bibliographies.
- **Zhou et al.:** the abstract mentions initialization heuristics but not the name "INTERP", so the notebook says "interpolation, following Zhou et al.".
- **"No earlier quantum approach that models IM"** rests on the brief's earlier GitHub search plus the two papers checked tonight. No new broad search was done.
- **Vandelli et al.'s body** was read through a fetch tool's summary of the arXiv HTML page, not line by line.
- **Venue:** "Shure ULD" is copied verbatim; the model and its band are unknown. The Line-6 units' band could not be confirmed, so they are left out.

## Decisions and fallbacks

- **`QAOAAnsatz` → `qaoa_ansatz`.** The class is deprecated in Qiskit 2.1 and later. The function rejects a circuit mixer, so the XY mixer goes in as a `SparsePauliOp` with even-pair terms first. Checked: the synthesis equals the agreed product.
- **Fast path for tuning, disclosed in the notebook** (the brief's expected route). The real circuit confirms it.
- **CVaR (alpha 0.1) kept over the mean.** Alpha 0.15 and 0.25 gave the same p = 3 result.
- **p = 3 on the circuit.** p = 4 and 5 are fast-path only, to keep the runtime down.
- **`StatevectorEstimator` used at 8 qubits only.** At 16 qubits it took about 50 s.
- **Six mics kept classical** (21 points, 2 clean plans out of 54,264). A 21-qubit circuit would break the budget.
- **Plots and kernel.** Static PNGs on a light background, with a palette checked for colour-blind safety. Kernel registered with `--sys-prefix`, and the notebook's kernel name is `python3`.
- **Render tooling.** `comtypes` was installed in the venv for the PowerPoint render check. It is not in `requirements.txt`, because only the render script needs it.
- **Exclusions include their edges.** "472.0-472.5 MHz" removes three points.
- All decisions agreed with Lucas before the build are listed in `PROGRESS.md`.

## Known issues

- Runtime varies between runs (81 to 116 s here). Brute-force timing varies too (6 to 12 ms), so the slides say "about 10 ms".
- The earlier estimates (89 QUBO variables, about 5,700 CNOTs per cost layer) did not reproduce. The corrected numbers are logged in `PROGRESS.md`.
- Placeholders remain: `[Team name]`, `[Member 1]` to `[Member 4]`, plus the "what did AI do" gap in `team/judge_qa.md` and `team/explainer_4_story_and_demo.md`.
- `plan_mics` refuses grids above 20 points, by design.
- The figures in `figures/` come from `tools/make_figures.py`, not from the notebook, but they use the same code and seeds and give the same numbers.

## Suggested next steps, Wednesday to Friday

**Everyone**
- Read `team/limitations.md` and `team/judge_qa.md`. Each of you should be able to answer every question.
- Fill in the placeholders and the "what did AI do" answer truthfully.
- Confirm the judging time (the brief lists both 5:30 to 8:30 PM and 6:30 to 9:00 PM).

**[Member 1]: problem and engine**
- Work through `explainer_1_problem_engine.md` and rerun the engine cells.
- Optional: add a notebook example on a finer grid (say 125 kHz steps over a narrower band) where the guard catches near misses. That shows the engine going beyond the Golomb-ruler case.
- Stretch: fifth-order products.

**[Member 2]: quantum circuit**
- Work through `explainer_2_quantum_circuit.md`.
- Optional: build the cost layer as one `PauliEvolutionGate` per layer (2,570 CNOTs instead of 4,006), and compare depth and simulation time.
- Optional: transpile against a generic heavy-hex coupling map (for example `GenericBackendV2`, no account needed) to estimate routing overhead for the "hardware run" question.

**[Member 3]: results and baselines**
- Work through `explainer_3_results_and_baselines.md`.
- Optional: rerun sampling with several seeds and report the spread of the 7.1%.
- Optional: try w3 values and alpha values on the fast path and add a small table.
- Keep any new number in sync between the notebook, `figures/numbers.json` and the slides: rerun `tools/make_figures.py`, then `tools/build_slides.py`.

**[Member 4]: story and demo**
- Rehearse `team/demo_script.md` on the presentation laptop. Time it.
- Open the deck on the presentation machine and check fonts. Fill in slide 11.
- Practise the "Why quantum?" and "Isn't brute force instant?" answers aloud.
