# Judge Q&A

Short, honest answers. Numbers come from the notebook (seeds fixed: tuning 7, sampling 2026).

### 1. Why quantum?
Not for speed. The IM rules are three- and four-way interactions between frequencies. Gate-model QAOA takes them directly as 3- and 4-qubit Z terms on 16 qubits, and the Dicke start plus XY mixer keep exactly 5 mics with no penalty weight. The same problem as a QUBO needs 121 binary variables. We found no earlier quantum approach that models IM products.

### 2. Isn't brute force instant?
Yes. All 4,368 plans take about 10 ms. Greedy, simulated annealing and an integer program also solve it at once. We show that on purpose. The demo is a toy size that we can check exactly.

### 3. What about 40 mics?
40 carriers create 31,200 third-order products. On our kind of grid, 40 IM-free mics need at least 782 grid points, so 782 qubits, with about 152,000 triple terms and 39.6 million quadruple terms. Nobody can simulate that classically as a statevector, and today's hardware can't run it either. It would need a much sparser model or problem decomposition. Classical tools handle 40 channels today.

### 4. Why QAOA and not a quantum annealer?
Annealers take quadratic problems (QUBOs). Our triple and quadruple terms would need auxiliary variables: 121 instead of 16, plus penalties to hold them and the mic count in place. QAOA takes the higher-order terms as they are and fixes the count through the circuit. Both are heuristics with no proven advantage here.

### 5. Is this just a Golomb ruler?
On this demo instance, yes. With exact landings on a uniform grid and no neighbouring points, an IM-free plan is a Golomb ruler with no gap of 1. Babcock linked IM to these rulers in 1953. The engine handles other guards, steps and exclusions, where the problem differs, but the 16-point demo is that classic puzzle, and we say so.

### 6. How do you know the cost is right?
Four independent checks. The operator's diagonal matches the classical cost on every basis state at 12 qubits and all 65,536 at 16. Brute force reproduces the expected 24 clean plans out of 4,368. The checker recomputes every product from raw frequencies, separately from the cost terms. Every plan we report is re-checked product by product.

### 7. How do you know the circuit is right?
The Dicke circuit matches the exact Dicke state (fidelity 1.000000000000). The mixer never changes the mic count (largest leak about 1e-16). At the final angles, the full 12,716-CNOT circuit matches our exact NumPy simulation with fidelity 1.000000000000. The sampler's 7.1% IM-free agrees with the exact 6.96% within shot noise.

### 8. What did AI do in this project?
An AI coding assistant wrote the first version of the code, notebook, slides and team notes overnight from a brief our team wrote. The brief chose the problem, set the rules and required honest reporting. [Each member: say what you checked, reran or rewrote.] Every number traces to code that anyone can rerun.

### 9. What would a hardware run need?
A device with 16 good qubits, plus routing on its coupling map, which adds SWAPs. We'd start at p = 1 with the leaner cost-layer synthesis (2,570 CNOTs instead of 4,006), plus 560 for the Dicke state, and use error mitigation. Then we'd compare the IM-free share against 0.55% random. We have not run it, and we expect noise to wash out much of the signal at this depth.

### 10. How does it compare with Shure Wireless Workbench?
Workbench is free, mature and far more complete: scan data, device inventory, many bands. We don't compete with it. Our contribution is a quantum modelling route for IM and a plain-English interface on top.

### 11. QAOA only finds a clean plan 7% of the time. Isn't that bad?
It is about 13 times better than random (0.55%), but every classical method finds a clean plan instantly. On our exact simulation, 5 layers reach 12%. We report it as it is.

### 12. You tuned the angles on a classical computer. Isn't that cheating?
It is standard for small QAOA studies, and we disclose it. The tuned angles then run on the real Qiskit circuit, and the results match. It doesn't scale, and we list that as a limitation.

### 13. Why the Dicke state?
It is an equal mix of every 5-mic plan, so the search starts exactly where a random planner would. The usual all-|+> start includes plans with any number of mics and would need a penalty.

### 14. Why the XY mixer?
XX + YY swaps a 1 and a 0 between neighbouring qubits, which moves a mic without adding or removing one. The usual X mixer flips single bits, which changes the mic count.

### 15. Why CVaR?
We only need one clean plan, so we care about the best outcomes, not the average. CVaR with alpha 0.1 scores the best 10% of outcomes. It reached 6.96% at p = 3, against 3.87% for the plain average.

### 16. Why 250 kHz and 500 kHz?
Shure's guide says most manufacturers recommend at least 250 kHz between any third-order product and any carrier. The 500 kHz carrier spacing is our demo choice, and we label it as one.

### 17. Why only third-order products?
They are the strongest products that land near the carriers. Fifth-order products also land in band, and adding them is first on our list. They would add five-body terms.

### 18. Does the weight w3 matter?
Not for which plans are clean: a clean plan scores 0 for any positive weight. It can affect how well QAOA trains. We kept w3 = 1.

### 19. Why does the circuit need 12,716 CNOTs?
948 Z-strings, mostly of weight 3 and 4. Each needs a CNOT ladder (6 CNOTs for a weight-4 term). That is the price of putting the IM rules in directly.

### 20. Is the venue's band real?
No. The Humanities Theatre's spec sheet lists six Shure wireless channels but no frequency band. 470 to 474 MHz is illustrative, and so is the exclusion.

### 21. What is new compared with earlier work?
D-Wave's frequency-selection example models forbidden spacings between frequencies. Vandelli et al. (2025) model pairwise interference between antenna sites with a constraint-preserving quantum algorithm. Neither models intermodulation. Constraint-preserving mixers themselves are not new (Hadfield et al., Wang et al.).

### 22. Why 16 qubits?
16 grid points keep the full circuit simulation at about 15 seconds and the notebook under 2 minutes. Six mics would need 21 points, with only 2 clean plans out of 54,264.

### 23. Can I run it myself?
Yes. Install the packages in `requirements.txt` and run the notebook top to bottom. It takes under two minutes on our laptop, and nothing is precomputed.
