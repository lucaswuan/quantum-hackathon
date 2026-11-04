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
