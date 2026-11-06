# Progress log

Blockers: none so far.

## Pre-build review (November 3, evening)

The folder held only the build brief. Checks on this laptop:

- Python: only 3.14.8 is installed (`py -0`). There is no 3.13 or 3.12 to fall back to.
- Git 2.55 is installed, with a global identity (Lucas Wu). Commits stay local.
- PowerPoint is registered for COM. LibreOffice is not installed.
- Power: never sleeps on AC, sleeps after 15 minutes on battery. Keep-awake was requested through the app.

### Numbers recomputed before the build (pure Python script)

| Quantity | Brief | Recomputed |
|---|---|---|
| Five-mic plans on 16 points | 4,368 | 4,368 |
| Plans meeting the spacing rule | 792 | 792 |
| IM-free plans | 24 | 24 |
| Pair, triple, quadruple terms | 15, 56, 252 | 15, 56, 252 |
| Distinct Z-strings | 948 | 948 (16, 120, 560, 252 by weight) |
| Clean plans under the inclusive 250 kHz reading | 0 | 0 |
| Naive CNOTs per cost layer | about 5,700 | 3,992 (2(w-1) per string, before transpiling) |
| Variables as a QUBO (greedy Rosenberg) | 89 | 121 (105 auxiliary); 114 to 134 across tie-break orders |
| Two-tone, three-tone products at 40 carriers | 1,560, 29,640 | 1,560, 29,640 |
| Smallest grid for 6 IM-free mics with spacing | "at least 18" | 21 points, 2 clean plans |

Greedy check: deterministic greedy (lowest frequency first, fewest new conflicts) returns {0, 2, 5, 9, 15}, which is clean. Starting from each of the 16 points in turn, 8 of 16 runs end clean. The evenly spaced plan {0, 3, 6, 9, 12} has 4 two-tone and 3 three-tone conflicts.

### Sources re-opened

- Shure IMD page: "most manufacturers recommend a minimum margin of 250kHz" between any 3rd-order product and any carrier. Three transmitters "may generate six in-band 3rd order and three in-band 5th order IM products". No carrier-to-carrier spacing given, so 500 kHz stays labelled as a demo choice.
- UW Theatres: Humanities Theatre in Hagey Hall seats up to 721. Tech specs list 3 Shure ULD handhelds, 3 Shure ULD body-packs, 4 Line-6 handhelds, 3 Line-6 body-packs, and a "Clear-Comm" base station with 6 wireless packs. No frequency bands or receiver models.
- SoundPro 2026 guide: the "40 or more simultaneous wireless channels" sentence is there, and it names Wireless Workbench, Sennheiser WSM and PWS IAS.
- D-Wave frequency-selection example: demand plus forbidden-spacing interference only. No IM.
- Vandelli, Ferrari, Dragoni (arXiv 2511.15566): multi-frequency antenna placement, pairwise overlap cost between sites at frequencies p and p', a quantum adiabatic algorithm with a custom constraint-preserving mixer. No IM.

## Decisions (approved by Lucas before the build)

1. Red plan for the demo: the evenly spaced newcomer plan (470.00, 470.75, 471.50, 472.25, 473.00 MHz). Report greedy's results beside it, including that greedy solves the demo.
2. Exclusions: benchmark and story on the plain 16-point grid. A second `plan_mics` call with an illustrative exclusion (13 qubits). Say openly that the 16-point instance is a Golomb-ruler search with no gap of 1.
3. No single best plan: 24 plans tie at zero cost. Report the IM-free share and the most-sampled clean plan. No tie-breaker.
4. Story: five of the Humanities Theatre's six Shure channels. The 6-mic case (21 points, 2 clean plans) is a classical "beyond the toy size" figure. Don't guess the Shure model or band. Leave the Line-6 units out.
5. Wording: "we found no earlier quantum approach that models IM products".
6. Cost: one term per conflicting set. The checker lists every product.
7. Corrections accepted: QUBO size, CNOT count, mixer written as a product, Shure wording, Vandelli et al., exclusive upper band edge.
8. Defaults: kernel via `--sys-prefix`, notebook kernel name `python3`, pip `--no-cache-dir`, switch from `QAOAAnsatz` only if deprecated, `plan_mics` never swaps in brute force silently, target notebook runtime of 3 minutes or less.

### Extra note found after approval

- Shure Wireless Workbench appears to be a free download. If confirmed, the "school AV tech with no software" story is weak on its own. Frame the pitch around the plain-English interface and the quantum modelling route, and say in the Q&A that free vendor tools exist and are far more complete.

## Phase log

### Phase 0: setup (done)

- Venv on Python 3.14.8. Installed with `--no-cache-dir`: qiskit 2.6.1, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2, jupyter 1.1.1, nbconvert 7.17.2, ipykernel 7.4.0, python-pptx 1.0.2, pytest 9.2.0. Pinned in `requirements.txt`.
- Smoke test: Bell state on `StatevectorSampler` (seed 7) gave 502 `00` and 498 `11`. `StatevectorEstimator` gave <ZZ> = 1.0.
- Kernel registered with `--sys-prefix` as `python3` inside `.venv`.
- **`QAOAAnsatz` is deprecated** in 2.6.1 (the NLocal and BlueprintCircuit classes were deprecated in Qiskit 2.1, removal in 3.0). Switched to the `qaoa_ansatz` function, as agreed.
- `qaoa_ansatz` rejects a circuit as `mixer_operator`, so the XY mixer is passed as a `SparsePauliOp` with the even-pair terms listed before the odd-pair terms. Checked at 4 and 6 qubits: after transpiling (levels 0 to 3) the synthesized mixer equals exp(-iβH_odd) exp(-iβH_even) up to global phase, and does not equal exp(-iβH_XY). This matches the agreed mixer correction.
- Gotcha: `Operator(PauliEvolutionGate)` returns the exact exponential, not the synthesized circuit. Always transpile before checking or simulating. At 16 qubits an untranspiled evolution gate could also be turned into a dense matrix, so the sampler always gets a transpiled circuit.
- `RXX(β) RYY(β)` equals exp(-iβ(XX+YY)/2), and so does `XXPlusYYGate(2β)`.

### Phase 1: engine (done)

- `micplanner/engine.py`: parsing ("470-474 MHz", "250 kHz", "470 MHz to 474 MHz"), grid with the top edge excluded and exclusion edges included, P/T/Q enumeration with a strict "less than the guard" test, a checker that lists every product, cost on bit masks, brute force.
- All frequencies are whole hertz, so guard tests never depend on float rounding.
- Confirmed by tests (`tests/test_engine.py`, 9 passing): 16 points; 15, 56, 252 sets; 4,368 plans, 792 well spaced, 24 IM-free; {0, 2, 5, 9, 15} clean; inclusive guard gives 0 clean plans; the exclusion example leaves 13 points; the evenly spaced plan has 8 two-tone and 12 three-tone hits (4 triples and 3 quadruples, cost 7).
- Decision: an exclusion range includes its edges. "472.0-472.5 MHz" removes 472.000, 472.250 and 472.500.

### Phase 2: cost operator (done)

- `micplanner/cost.py`: HUBO with one term per conflicting set, Pauli-Z expansion as a `SparsePauliOp` (identity kept, so the diagonal equals C(x) exactly), diagonal check, Z-strings by weight, naive CNOT count, greedy Rosenberg counter.
- Diagonal check: exact on every basis state for 10- and 12-point instances (Qiskit `to_matrix`). At 16 qubits: 16 to 64 random states through `Statevector.expectation_value`, plus all 65,536 states by direct parity. Max error 0.
- 948 Z-strings: 16, 120, 560, 252 by weight. Naive CNOTs 3,992 per cost layer.
- QUBO: deterministic greedy Rosenberg needs 105 auxiliary variables, so **121 variables** against 16 qubits. Over 200 random tie-break orders the range is 114 to 125. The slide line will be "16 qubits here vs 121 variables as a QUBO" with the range in the notes.
- w3 only rescales the IM terms. Clean plans stay at cost 0 for any w3 > 0 (tested at 0.5 and 2).

### Phase 3: small run, 8 points and 3 mics (done)

- `micplanner/quantum.py`: Bärtschi-Eidenbenz Dicke circuit, XY ring mixer (operator and explicit RXX/RYY versions), `qaoa_ansatz` with Dicke start and XY mixer, name-based angle binding, transpile to `['cx', 'rz', 'sx', 'x']`, `StatevectorSampler` sampling, exact NumPy fast path on the n-mic subspace, COBYLA tuning (grid scan for p = 1, then INTERP plus seeded random starts), circuit-vs-fast-path comparison, resource card.
- The Dicke construction worked first time: exact for every n up to 8 and every k, and for (16, 5) after transpiling.
- XY mixer keeps the Hamming weight exactly (n = 4 to 7). Synthesized mixer equals the group product (n = 4, 5, 6). For an odd ring the wrap-around pair gets its own group, so a 13-point instance uses three groups.
- Small instance: 8 points, 3 mics, 56 plans, 14 clean (25%). Fast path vs circuit at p = 2: fidelity 1.0, leakage 1e-14. Mean objective: P(clean) 0.53, 0.82, 0.88 for p = 1, 2, 3. Sampled at p = 2 with 4,000 shots: 83.3% clean against 82.2% exact and 25% random.
- CVaR with alpha 0.2 is flat here because 25% of plans already cost 0, more than alpha. It should behave differently at demo size, where only 0.55% are clean.
- `tests/test_quantum.py`: 20 tests passing.

### Phase 4: full run, baselines, figures (done)

Demo instance: 470-474 MHz, 250 kHz step, 16 points, 5 mics, 500 kHz spacing, 250 kHz IM guard. All numbers below come from `make_figures.py` (written to `figures/numbers.json`) with fixed seeds (tuning 7, sampling 2026).

- **Fast path vs circuit at 16 qubits (p = 3):** fidelity 1.0000000000, leakage 7e-14, max amplitude difference 2e-15. The Statevector run of the 12,716-CNOT circuit takes about 15 to 19 s.
- **Exact IM-free probability by layer** (fast path):

  | p | Mean of C | CVaR, alpha 0.1 |
  |---|---|---|
  | 1 | 1.75% | 1.85% |
  | 2 | 3.35% | 4.03% |
  | 3 | 3.87% | 6.96% |
  | 4 | 3.66% | 10.00% |
  | 5 | 3.94% | 12.12% |

  Uniform random is 0.55%. CVaR gives more IM-free samples, so it is the objective kept, as the brief asks. Alpha 0.1, 0.15 and 0.25 all reach the same p = 3 optimum. The mean objective stalls near 4%. The circuit runs at p = 3. p = 4 and 5 come from the fast path only, to keep the notebook runtime down, and are labelled that way.
- **Sampled on the circuit:** 8,000 shots at p = 3 with CVaR angles give 7.1% IM-free samples (exact 6.96%), about 13 times uniform random. The most common clean sample is {470.000, 470.500, 471.500, 472.750, 473.500} MHz, at 0.5% of shots. With 24 clean plans tied, no single plan dominates, as agreed.
- **Exclusion case** (472.0-472.5 MHz kept clear): 13 points, 1,287 plans, 8 clean (0.62%). QAOA at p = 3 gets 10.8% IM-free samples. Plan {470.000, 470.500, 471.250, 472.750, 473.750} MHz.
- **Baselines** (all solve the demo instantly): brute force 10 ms (24 clean of 4,368); greedy 2 ms, returns {0, 2, 5, 9, 15}, clean; greedy from each of the 16 starting points: 8 of 16 clean; simulated annealing with swap moves: 50 of 50 runs clean in 0.08 s; SciPy `milp`: optimal in 0.1 s; 8,000 uniform random plans: 0.50% clean.
- **Newcomer plan** {470.00, 470.75, 471.50, 472.25, 473.00}: 8 two-tone and 12 three-tone hits (20 in all), cost 7.
- **Resource card** (basis `cx, rz, sx, x`, level 1): Dicke 560 CX; cost layer as built by `qaoa_ansatz` 4,006 CX (naive ladder count 3,992; 2,570 if the whole layer is synthesized as one `PauliEvolutionGate`, which shares ladders); mixer 46 CX; full p = 3 circuit 12,716 CX, depth 12,076. Transpiling takes about 0.1 s. Level 2 or 3 brings the full circuit to 12,536 CX but simulates slower, so level 1 stays.
- **6-mic case:** 21 points, 54,264 plans, 2 clean ({0, 2, 8, 13, 17, 20} and its mirror). Kept as a classical figure, as agreed. A 21-qubit circuit run would take minutes, which breaks the budget.
- **StatevectorEstimator** at 16 qubits took about 50 s for <C>, <N>, <N^2>. It gave <C> equal to the fast path to 1e-12, <N> = 5 and <N^2> = 25 (zero variance in the mic count). Too slow for the notebook at 16 qubits, so the notebook uses it on the 8-point instance and uses `Statevector` for the 16-qubit fidelity check.
- Figures in `figures/`: ghost example, product growth, story and exclusion spectra, newcomer plan, newcomer vs QAOA, histogram, convergence, IM-free share by layer. Static PNGs on a light background. Palette checked with the dataviz validator (blue/orange pass every check). Red is used only for hits, always with an x marker and a label.
- Decision: the brief's "greedy with red hits" panel uses the newcomer plan instead, as agreed. Greedy's clean result is reported beside it.

### Phase 5: notebook (done)

- `mic_planner.ipynb` is generated by `tools/build_notebook.py` (50 cells: title plus nine sections, as in section 6.5 of the brief, with references last). Executed in place with outputs saved.
- **Headless check:** `jupyter nbconvert --to notebook --execute --inplace mic_planner.ipynb` takes **81 s** wall-clock. The in-notebook timer reads 77 s. No errors, no warnings in cell outputs.
- Everything runs live. Nothing is precomputed or loaded, and the notebook says so. The fast-path tuning is disclosed in section 5 and confirmed on the real circuit (fidelity 1.0 at 16 qubits).
- `StatevectorEstimator` runs on the 8-point instance (<C> matches the fast path to 10 digits, <N> = 3, variance 1e-13). `Statevector` handles the 16-qubit check, which is faster.
- References re-opened tonight: arXiv abstracts for 1411.4028, 1709.03489, 1904.07358, 1904.09314, 1907.04769, 1812.01041 and 2405.08810. Babcock 1953 (BSTJ 32:63-73) via the Wikipedia Golomb ruler article's reference list. Rosenberg 1975's title is from later bibliographies, not the journal itself. Zhou et al.'s abstract mentions "heuristic strategies for initializing" but not the name INTERP, so the notebook says "interpolation, following Zhou et al.".
- Shure's Wireless Workbench page confirms it is free ("our free software for audio professionals"). This goes into the limitations and the Q&A.
- `tools/show_outputs.py` prints every cell's output for review without Jupyter.
- New helper `engine.uniform_grid_term_counts` gives T and Q on a uniform grid. Tested against enumeration at 5, 9 and 16 points. 40 mics need at least 782 grid points: 152,490 triple and 39,621,985 quadruple terms.

### Phase 6: slides (done)

- `slides/mic_planner_deck.pptx`: 12 slides at 16:9, built with python-pptx by `tools/build_slides.py`, which reads its numbers from `figures/numbers.json`. Calibri throughout, one accent colour (the chart blue), dark title and team slides, light content slides. Titles 36 to 48 pt, body 18 to 26 pt, two 14 pt source lines. At most five bullets per slide. Speaker notes on every slide.
- `slides/deck_outline.md` is written by the same script: slide text plus speaker notes.
- Follows the brief's suggested flow (title, problem, why it's hard, tool, bridge, demo, results, why quantum, shortfalls, next, team, references).
- File check: the pptx skill's `validate.py` passes.
- **Render check: Microsoft PowerPoint through COM** (`comtypes` added to the venv, render script `tools/render_slides.py`, output in `slides/render/`, git-ignored). Every slide inspected. First pass fixes: chart titles repeating the slide titles (slide versions of three figures now drop them), dead space on slides 4, 5 and 8, a growth-chart label sitting on a curve, a brute-force time that varies between runs (now "4,368 plans in about 10 ms"), and a role label wrapping into the card text. Second pass: no overflow or overlaps.
- PowerPoint was not running before, and the script quits it afterwards.
- Decision: slide 9 says "12,716 CNOTs at p = 3, and not run on hardware" rather than claiming the circuit is too deep for today's devices, which we have not tested.

### Phase 7: team docs (done)

- `team/explainer_1_problem_engine.md`, `explainer_2_quantum_circuit.md`, `explainer_3_results_and_baselines.md`, `explainer_4_story_and_demo.md`: one per role, each with what the part does, how it works in plain words, where the code lives, numbers to remember and likely questions.
- `team/judge_qa.md`: 23 questions, including every one the brief lists.
- `team/demo_script.md`: a 2 to 3 minute live demo with what to click and say, plus a fallback.
- `team/limitations.md`: an honest list.
- `README.md`: what it is, three commands to run it, headline numbers, folder map, how to rebuild generated files.
- Style pass: no em or en dashes in any deliverable (the only en dash is in the parser's regex, so users can type "470–474"). No American spellings in prose; "color" and "center" appear only as library argument names.
- Decision: the "What did AI do?" answers say an AI coding assistant wrote the first version from the team's brief, and leave a bracketed gap for each member to say what they checked or changed. Only the team can fill that in truthfully.
- Removed one unsourced RF claim (about in-ear monitor racks) from the limitations draft.

### Phase 8: final check (done)

- Notebook rebuilt from `tools/build_notebook.py` and executed in a fresh kernel with `jupyter nbconvert --to notebook --execute --inplace mic_planner.ipynb`: **115.6 s** wall-clock (in-notebook timer 109 s). No errors or warnings in any cell. Same numbers as before (7.11% IM-free samples, fidelity 1.0, 121 QUBO variables, same plans).
- Runtime varies run to run on this laptop: 80.8 s, 81.1 s, 115.6 s and 94 s for the four full headless runs. The fourth ran on a temporary copy, `_timing_check.ipynb`, deleted afterwards. It gave the same outputs. All are well under the 5-minute limit. The docs now say "under two minutes".
- `pytest`: 35 passed.
- `FINAL_REPORT.md` written.

## November 4: pushed to GitHub

- Lucas asked for everything to go to https://github.com/lucaswuan/quantum-hackathon (a new, empty, public repo). This overrides the brief's "keep it local" rule for this repo.
- Before pushing, the tracked files were scanned for secrets, emails and local paths. None were found. `.venv/` and `slides/render/` stay git-ignored.
- The deck's metadata had python-pptx's stock "last modified by" name. `tools/build_slides.py` now sets title and author to neutral values. The slide content is unchanged.

## November 5: submission fixes

The submission form takes one `.ipynb` file, so the notebook has to run with nothing beside it.

- **The problem:** uploaded alone, the old notebook stopped at its first code cell with `ModuleNotFoundError: No module named 'micplanner'`.
- **The fix:** a new Setup section checks for packages and installs any that are missing. Collapsed cells then write the seven `micplanner` files into `micplanner_embedded/` with `%%writefile`. That folder goes at the end of `sys.path`, so a real `micplanner/` folder next to the notebook still wins and never gets overwritten.
- `tools/build_notebook.py` copies the code straight from `micplanner/*.py`. `tests/test_notebook.py` fails if the two differ. `tools/run_standalone.py` runs the notebook alone in an empty temporary folder and saves its outputs, so the saved outputs come from the embedded code.
- Decision: packages are installed only if missing, or if Qiskit is older than 2.1. If the version isn't 2.6.1, the notebook prints a note that gate counts may differ.
- **Tests, each with only the `.ipynb` in an empty folder:**

  | Setup | Wall-clock | Result |
  |---|---|---|
  | Project venv, Qiskit 2.6.1 | 102 s, 121 s | Same numbers |
  | Brand-new venv with no Qiskit, installed by the notebook | 197 s | Same numbers |
  | Qiskit 2.1.0 | 100 s | Same numbers |
  | Qiskit 2.6.2 | 101 s | Same numbers |

  Same numbers means 7.11% IM-free samples, fidelity 1.0 and 12,716 CNOTs. A static check found nothing that would stop the code parsing on Python 3.10, but only Python 3.14 on Windows was actually run.
- **Slide maths:** slide 5 used rare Unicode subscript characters that Calibri doesn't have. They rendered here through font fallback and can break elsewhere. Slide text now uses real subscript formatting, the cost function on slide 5 is a typeset image (`figures/fig_cost_equation.png`), and the chart labels on slides 2 and 3 use Matplotlib's maths text.
- **Incident:** `tools/render_slides.py` attached to a PowerPoint that was already open, and its `Quit` very likely closed it. The deck had been locked seconds earlier, and PowerPoint was gone right after. The saved deck had no edits. The script now refuses to run while PowerPoint is open.
