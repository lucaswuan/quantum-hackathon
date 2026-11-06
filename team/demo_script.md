# Live demo script (2 to 3 minutes)

**Before judging:** open a terminal in the project folder and start Jupyter with the venv:

```
.venv\Scripts\jupyter notebook mic_planner.ipynb
```

Run the notebook once with Kernel, Restart and Run All, so every output is fresh and the kernel is warm. Then scroll back to the top. Keep the slides open on slide 6 in another window.

---

**0:00. Set the scene** (slide 6 on screen)

> "Here's what goes wrong. A newcomer spaces five mics evenly. Every red cross is a ghost signal landing right on a mic: 20 hits. Our planner's plan, underneath, has none. Let's run it live."

*Switch to the notebook. Scroll to section 2, "Using the tool".*

**0:20. Run the tool**

*Click the `plan_mics(...)` cell. Press Shift and Enter.*

> "This is the whole interface. A band, five mics, a grid step, a spacing and a guard, in plain units. No Hamiltonian, no penalty weights."

*While it runs (about 30 seconds):*

> "Under the hood, each of the 16 frequencies is a qubit. The IM rules become 948 Z-terms, some touching four qubits at once. QAOA starts from every five-mic plan at once and runs on Qiskit's statevector sampler. The circuit can never add or remove a mic."

**0:55. Read the result**

*Point at the printed report, then the spectrum.*

> "Five frequencies, and the checker confirms no product lands within 250 kilohertz of any mic. About 7 percent of the 8,000 samples were clean plans. A random plan is clean about half a percent of the time. Blue lines are mics, grey lines are the ghosts, and they all miss."

**1:20. Show an exclusion**

*Scroll to the exclusion cell. Shift and Enter (about 6 seconds).*

> "Say 472 to 472.5 is taken. One extra argument. Three frequencies drop out, so this run uses 13 qubits, and it still finds a clean plan."

**1:40. Be honest** (switch to slide 8)

> "Now the honest part. Brute force checks all 4,368 plans in about 10 milliseconds, and greedy also solves it. We don't claim a speed-up. What we do claim: QAOA takes the three- and four-way IM rules directly on 16 qubits, where a QUBO needs 121 variables, and the circuit keeps the mic count without penalties. We found no earlier quantum approach that models IM."

**2:20. Close**

> "Everything here reruns from scratch in about two minutes. Happy to take questions."

---

**If something goes wrong**

- **The cell is slow or the kernel dies:** say "here's the saved output from the same seeds" and scroll through the outputs already in the notebook.
- **The numbers differ slightly from the slides:** they shouldn't with fixed seeds, but brute-force timing changes run to run. Say "about 10 ms".
- **No internet is needed.** Everything runs locally.
