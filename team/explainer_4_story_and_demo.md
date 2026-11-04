# Explainer 4: the story, the slides and the demo

**Role:** [Member 4]. You own `micplanner/api.py` (`plan_mics`), the slides and the live demo.

## The pitch in 30 seconds

Wireless mics create ghost signals when they transmit together. If a ghost lands on another mic, it crackles. Pros avoid this with vendor software or an RF coordinator. We built a plain-English planner: you describe the band and the mics, and it returns a clean frequency plan. Underneath, the IM rules become three- and four-way interactions between qubits, and QAOA searches them with a circuit that always keeps exactly five mics. It doesn't beat classical methods, and we don't claim it does. It is a working bridge from a real sound-engineering problem to a quantum algorithm.

## The story and what is real

- **Real, checked tonight:** the Humanities Theatre in Hagey Hall seats up to 721 (UW Theatres, "Our theatres"). Its technical specs list 3 Shure ULD handheld microphones and 3 Shure ULD wireless body-pack transmitters (UW Theatres, Humanities Theatre technical specs).
- **Our scenario:** a show uses five of those six Shure channels.
- **Illustrative, not real:** the band 470 to 474 MHz and the exclusion 472.0 to 472.5 MHz. The venue pages give no bands or receiver models, and we did not look up local TV channels or Canadian licensing.
- **Left out on purpose:** the venue's Line-6 units and the Clear-Com intercom. We couldn't confirm their frequencies, so we don't claim anything about them.
- "ULD" is how the venue page writes the model. Don't guess what it stands for.

## What `plan_mics` does

```python
plan = plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz",
                 im_guard="250 kHz", exclude=["472.0-472.5 MHz"], csv_path="plan.csv")
```

1. Builds the grid and conflict lists (engine).
2. Builds the cost operator (one qubit per allowed frequency).
3. Tunes the angles on the exact fast path (CVaR, p = 3).
4. Runs the real circuit on Qiskit's `StatevectorSampler`, 8,000 shots.
5. Picks the most common IM-free sample and checks it product by product.
6. Prints a short report, draws the spectrum and writes a CSV.

If no clean plan turns up in the samples, it says so and shows the best sample with its problems. It never quietly swaps in brute force. It refuses grids over 20 points, because the simulator would get too slow.

## Slide guide (12 slides, about 6 minutes plus demo)

| # | Slide | One line to say |
|---|---|---|
| 1 | Title | Plain-English mic planning with QAOA. Honest about what it is. |
| 2 | Two mics make two ghosts | The physics in one picture. |
| 3 | Products grow with the cube | 50 products from 5 mics, 31,200 from 40. |
| 4 | Our tool | One function call, a clean plan and a CSV. |
| 5 | The bridge | Rules, then conflict sets, then 948 Z-strings, then QAOA that keeps 5 mics. |
| 6 | Demo | Even spacing gives 20 hits. QAOA gives 0. Greedy also solves it. |
| 7 | How well it works | 7.1% IM-free against 0.55% random. |
| 8 | Why quantum, honestly | No speed-up. 16 qubits vs 121 QUBO variables. 12,716 CNOTs. |
| 9 | Where it falls short | Golomb ruler, toy size, third order only, not run on hardware. |
| 10 | What's next | Fifth order, real venues, scale, hardware. |
| 11 | Team | Who did what. Fill in the names. |
| 12 | References | Every number traces to the notebook. |

Speaker notes for every slide are in the deck and in `slides/deck_outline.md`.

## Running the demo

- Open `mic_planner.ipynb` in Jupyter with the project's `.venv`. The notebook is saved with its outputs, so you can show results even before running anything.
- The `plan_mics` cell in section 2 takes about 30 seconds on Lucas's laptop. The exclusion cell takes about 6 seconds. The whole notebook takes about 80 seconds.
- Full script: `team/demo_script.md`.
- **Backup:** if the live run is slow or fails, scroll to the saved outputs. They are from a real run with the same seeds.

## Numbers to remember

- 16 qubits, 5 mics, 4,368 plans, 24 clean (0.55%).
- 7.1% of QAOA samples clean, about 13 times random.
- Plan: 470.000, 470.500, 471.500, 472.750, 473.500 MHz.
- 16 qubits vs 121 QUBO variables.
- 12,716 CNOTs at p = 3.
- About 80 seconds to run the whole notebook.

## Likely questions

**Why this venue?** It is on campus and its spec sheet lists six Shure wireless channels, so the scenario is realistic. We don't claim to know its real frequencies.

**How does it compare with Shure Wireless Workbench?** Workbench is free, mature and far more complete: scan data, device control, many bands. Ours is a research prototype. Our contribution is the quantum modelling route and the plain-English interface, not a replacement.

**Could a school really use this?** Not for a real show today. It plans on a toy grid with a simplified rule set. For a real show, use the vendor's free software.

**What did AI do?** An AI coding assistant wrote the first version of the code, notebook, slides and these notes overnight, from a brief our team wrote. The brief set the problem, the rules and the honesty requirements. [Fill in what each of you checked, changed or rewrote before Friday.]
