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
