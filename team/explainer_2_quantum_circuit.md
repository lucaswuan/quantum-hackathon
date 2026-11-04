# Explainer 2: the quantum circuit

**Role:** [Member 2]. You own `micplanner/cost.py` and the circuit parts of `micplanner/quantum.py`.

## What this part does

It turns the conflict lists from the engine into a quantum operator, and builds the QAOA circuit that searches for a plan. The circuit starts from every possible 5-mic plan at once and nudges the odds toward clean plans.

## Step 1: the cost function

Each grid point k gets a bit x_k. It is 1 when a mic sits there. The cost adds 1 for every conflict that is fully switched on:

C(x) = sum over close pairs of x_k x_l + sum over triples of x_k x_l x_m + sum over quadruples of x_k x_l x_p x_m

- A plan is IM-free exactly when C = 0.
- The triple and quadruple sums carry a weight w3 = 1. Any positive w3 gives the same clean plans, because a clean plan scores 0 whatever the weights are. We checked w3 = 0.5 and 2.
- Each conflicting set counts once (15 + 56 + 252 terms), even though one triple causes two product hits.

## Step 2: from bits to qubits

On a qubit, Z measures +1 for |0> and -1 for |1>. So x_k = (1 - Z_k)/2. Substituting that into a product of w bits gives a sum over every subset of those w qubits, with signs. Do this for all 323 terms and collect:

- **948 Z-strings**: 16 with one Z, 120 with two, 560 with three, 252 with four.
- The result is a `SparsePauliOp` called H_C. It only contains Z's, so it is **diagonal**: each basis state (each plan) just gets its cost on the diagonal.
- **Check:** we compared the diagonal with the classical cost on every basis state at 12 qubits (with Qiskit's own matrix) and on all 65,536 states at 16 qubits. The largest difference was 0.

Because H_C is diagonal, exp(-i gamma H_C) just multiplies each plan by a phase. Bad plans spin faster than good ones.

## Step 3: the Dicke start

- The Dicke state |D^16_5> is an equal mix of all 4,368 strings with exactly five 1s, so every 5-mic plan starts with equal weight.
- Measuring it straight away gives a **uniform random plan**. That is our random baseline: 0.55% IM-free.
- We build it with the deterministic circuit of Bärtschi and Eidenbenz (2019). It works like dealing cards: a chain of "split and shift" blocks that each decide, with the right probability, whether a mic goes on the last free qubit.
- **Check:** exact for every n up to 8 and every k, and fidelity 1.000000000000 for (16, 5) after transpiling. It costs 560 CNOTs.

## Step 4: the XY mixer

- For each pair of neighbouring qubits, the gate exp(-i beta (XX + YY)/2) leaves |00> and |11> alone and rotates |01> into |10>. In words: it can **move a mic one step**, but never adds or removes one.
- We apply it to the even pairs (0,1), (2,3), ..., then the odd pairs (1,2), ..., (15,0). With an odd number of qubits, the pair that closes the ring gets its own group.
- The mixer is the product U_M = exp(-i beta H_odd) exp(-i beta H_even). This is **not exactly** exp(-i beta H_XY), because neighbouring pairs don't commute. The circuit does the product, and our fast simulation does the same product.
- **Check:** on 4 to 7 qubits, no amplitude ever moves between different mic counts (largest leak about 1e-16). The synthesized mixer equals the even-then-odd product exactly.
- So every sample has exactly 5 mics, with **no penalty weight**. That is the main design point.

## Step 5: the QAOA circuit

- One layer is: the cost phase exp(-i gamma H_C), then the mixer U_M(beta). We use p = 3 layers, so 6 angles.
- We build it with Qiskit's `qaoa_ansatz` function. The older `QAOAAnsatz` class is deprecated since Qiskit 2.1, so we switched.
- `qaoa_ansatz` only accepts the mixer as an operator, not a circuit. We pass H_XY with the even-pair terms listed first, and Qiskit builds it term by term in that order, which gives exactly our product.
- The angles are named γ[0..2] and β[0..2]. We bind them by name, never by position.
- We transpile to `cx, rz, sx, x` before simulating. One trap: `Operator(PauliEvolutionGate)` gives the ideal exponential, not the built circuit, so checks must transpile first.

## Resource card (p = 3, transpile level 1)

| Piece | CNOTs |
|---|---|
| Dicke start | 560 |
| One cost layer as `qaoa_ansatz` builds it | 4,006 (naive count 3,992) |
| Same layer built as one gate | 2,570 |
| One mixer layer | 46 |
| Full circuit | 12,716, depth 12,076 |

**The QUBO comparison.** A QUBO allows only pairs. Each triple or quadruple needs helper variables y = x_i x_j, held in place by a Rosenberg penalty. Our counter repeatedly replaces the pair that appears in the most big terms. Result: **121 variables** instead of 16 qubits (114 to 125 depending on how ties are broken), plus a penalty to hold the mic count at 5.

## Where the code lives

| What | Where |
|---|---|
| HUBO terms, Pauli conversion | `cost.hubo_terms`, `cost.hubo_to_pauli`, `cost.cost_operator` |
| Diagonal check | `cost.check_diagonal` |
| QUBO size | `cost.quadratize_greedy`, `cost.qubo_size` |
| Dicke circuit | `quantum.dicke_circuit` |
| Mixer | `quantum.mixer_groups`, `quantum.xy_mixer_operator`, `quantum.xy_mixer_circuit` |
| Ansatz, binding, transpile | `quantum.build_ansatz`, `quantum.angle_binding`, `quantum.compile_ansatz` |
| Resource card | `quantum.resource_card` |
| Tests | `tests/test_cost.py`, `tests/test_quantum.py` |

## Likely questions

**Why start in a Dicke state and not the usual all-|+> state?** All-|+> includes plans with any number of mics. We would need a penalty to push toward exactly 5, plus a weight to tune. The Dicke state only contains 5-mic plans.

**Why the XY mixer and not the usual X mixer?** An X gate flips one bit, which adds or removes a mic. XX + YY only swaps a 1 and a 0, so the count stays at 5.

**What is a four-qubit Z term physically?** It is a phase that depends on the parity of four qubits. On hardware it becomes a ladder of CNOTs, a Z rotation, and the ladder undone: 6 CNOTs for a weight-4 term.

**Why so many CNOTs?** 948 Z-strings, most of weight 3 or 4, each needing a CNOT ladder. That is the price of putting the IM rules in directly.

**Could you use fewer qubits?** Other encodings exist (for example, storing each mic's frequency as a binary number), but they need extra rules to stop two mics sharing a frequency. We didn't try them.

**Does w3 matter?** Not for which plans are clean. It changes how hard bad plans are punished, which can change how well QAOA trains. We kept w3 = 1.
