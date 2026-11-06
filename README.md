# IM-free wireless mic planner

A Qiskit Fall Fest 2026 project (University of Waterloo) by [Team name]: [Member 1], [Member 2], [Member 3], [Member 4].

Wireless mics that transmit together create intermodulation (IM) products, ghost signals that can land on another mic's frequency. This project plans mic frequencies with no third-order IM hits. You describe the band in plain words:

```python
plan_mics(band="470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz", im_guard="250 kHz")
```

Under the hood, each allowed frequency is a qubit. The IM rules become 3- and 4-qubit Z terms. QAOA starts in a Dicke state, and an XY mixer keeps the mic count fixed. It all runs on Qiskit's statevector simulator.

It is a heuristic with no speed-up: the 16-qubit demo is solved instantly by brute force. See the notebook's "Where it falls short" section and `team/limitations.md`.

## Run it in three commands

Needs Python 3.10 or newer (built and tested on Python 3.14.8, Windows).

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\jupyter notebook mic_planner.ipynb
```

Then use Kernel, Restart and Run All. The whole notebook takes about two minutes on our laptop. On macOS or Linux, use `.venv/bin/` instead of `.venv\Scripts\`.

`mic_planner.ipynb` also works as a single file with nothing else beside it. Its Setup section installs any missing packages and writes its own copy of the code into `micplanner_embedded/`. If a `micplanner/` folder sits next to it, as it does in this repo, Python uses that folder instead.

To run it headless: `.venv\Scripts\jupyter nbconvert --to notebook --execute --inplace mic_planner.ipynb`. To run the tests: `.venv\Scripts\python -m pytest`.

## Headline numbers (16 frequencies, 5 mics)

- 4,368 possible plans, 24 IM-free (0.55%).
- QAOA at p = 3 (CVaR objective): 7.1% of 8,000 samples IM-free, about 13 times random.
- 16 qubits here vs 121 binary variables for the same problem as a QUBO.
- Full circuit: 12,716 CNOTs at p = 3 (basis `cx, rz, sx, x`).

## Folder map

```
mic-planner/
  README.md                  this file
  requirements.txt           pinned direct dependencies
  mic_planner.ipynb          the deliverable notebook, saved with outputs
  micplanner/                the package the notebook imports
    engine.py                parsing, grid, exclusions, IM enumeration, checker, brute force
    cost.py                  HUBO to SparsePauliOp, diagonal check, QUBO size counter
    quantum.py               Dicke state, XY mixer, qaoa_ansatz, fast path, tuning, sampling, resource card
    baselines.py             brute force, greedy, simulated annealing, random, SciPy milp
    plots.py                 spectrum, histogram, convergence and other figures
    api.py                   plan_mics(...)
  tests/                     pytest tests (engine, cost, quantum)
  figures/                   PNGs for the slides, plus numbers.json with every number they quote
  outputs/                   CSV plans written by plan_mics
  slides/
    mic_planner_deck.pptx    12-slide deck with speaker notes
    deck_outline.md          slide text and speaker notes
  team/                      explainers, judge Q&A, demo script, limitations
  tools/                     scripts that build the figures, notebook and slides, and render the slides
  PROGRESS.md                build log with every decision
  FINAL_REPORT.md            morning summary
```

## Rebuilding the generated files

Edit the code in `micplanner/`, not the notebook's Setup cells. The notebook's copy is generated, and a test fails if the two drift apart. After changing the code, run `build_notebook.py` and then `run_standalone.py`.

```
.venv\Scripts\python tools/make_figures.py      figures/ and figures/numbers.json (about 80 s)
.venv\Scripts\python tools/build_notebook.py    mic_planner.ipynb with the code embedded, without outputs
.venv\Scripts\python tools/run_standalone.py    runs the notebook alone in an empty folder and saves its outputs
.venv\Scripts\python tools/build_slides.py      slides/ (reads figures/numbers.json)
.venv\Scripts\python tools/render_slides.py     slide PNGs through PowerPoint (needs comtypes and PowerPoint)
```
