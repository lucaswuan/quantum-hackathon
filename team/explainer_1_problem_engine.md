# Explainer 1: the problem and the engine

**Role:** [Member 1]. You own the radio physics and `micplanner/engine.py`.

## What this part does

The engine turns a plain description ("470-474 MHz, 5 mics, 250 kHz steps") into a list of allowed frequencies and a list of conflicts. It can also check any plan and say exactly which mics create which ghost signal and where it lands. Everything quantum later is built on these lists.

## The radio physics in plain words

- Every wireless mic transmits on its own frequency, called its **carrier**.
- Radio electronics are slightly non-linear. When two carriers meet, they mix and create new, weak signals called **intermodulation (IM) products**.
- The troublesome ones are **third-order** products. They land close to the carriers themselves:
  - **two-tone:** 2f1 - f2 and 2f2 - f1;
  - **three-tone:** f1 + f2 - f3.
- Products such as f1 + f2 land far away (around 940 MHz for our band), so they don't matter here.
- If a product lands on another mic's frequency, that mic's receiver hears it as noise or crackle.
- Shure's guide says "most manufacturers recommend" at least 250 kHz between any third-order product and any carrier. That is our **IM guard**.
- We also keep carriers at least 500 kHz apart. This is **our demo choice**, not a vendor rule. Shure's page gives no carrier-to-carrier spacing.

**Worked example.** Mics at 470.50 and 471.25 MHz give products at 2 x 470.50 - 471.25 = 469.75 and 2 x 471.25 - 470.50 = 472.00. A third mic at 472.00 would pick up a ghost.

## How the engine works

1. **Grid.** It lays a grid of candidate frequencies across the band. "470-474 MHz" at 250 kHz gives 470.000, 470.250, ..., 473.750: **16 points**. The top edge (474.000) is left out, because a carrier sitting exactly on the band edge would spill outside it.
2. **Exclusions.** Any point inside an excluded range is dropped, edges included. "472.0-472.5 MHz" removes three points, leaving 13.
3. **Conflict sets.** It lists three kinds of conflict:
   - **P (pairs):** two points closer than the spacing. On our grid these are neighbours: 15 pairs.
   - **T (triples):** a two-tone product 2f_k - f_l lands within the guard of a third point f_m. On our grid that means the three points are evenly spaced, like 470.00, 470.50, 471.00: 56 triples.
   - **Q (quadruples):** a three-tone product f_k + f_l - f_p lands within the guard of a fourth point f_m. On our grid that means two pairs with the same sum, like 470.00 + 471.00 = 470.25 + 470.75: 252 quadruples.
4. **"Within the guard" means strictly less than 250 kHz.** On a 250 kHz grid, that means landing exactly on a mic. A product exactly 250 kHz away is allowed. If we counted those too, no 5-mic plan on this grid would be clean (we checked).
5. **Checker.** `check_plan` takes any list of frequencies (on the grid or not) and lists every spacing problem and every product that hits a mic. One evenly spaced triple shows up as **two** two-tone hits, because 2b - a = c and 2b - c = a. One bad quadruple shows up as **four** three-tone hits.
6. **Brute force.** It scores all 4,368 five-mic plans at once with bit masks.
7. All frequencies are stored as whole numbers of hertz, so "less than 250 kHz" never depends on rounding.

## The Golomb ruler connection

On this grid, a plan is IM-free exactly when all the gaps between pairs of mics are different and none is 250 kHz. In maths that set is a **Golomb ruler** (or Sidon set) with no gap of 1. Example, in grid steps: {0, 2, 5, 9, 15} has gaps 2, 3, 4, 5, 6, 7, 9, 10, 13, 15, all different. Babcock linked IM-free channels to these rulers back in 1953. We say this openly. The engine itself handles any guard, step and exclusion, so it is more general than this one instance.

## Where the code lives

| What | Where |
|---|---|
| Parsing "470-474 MHz", "250 kHz" | `engine.parse_range`, `engine.parse_freq` |
| Grid and exclusions | `engine.make_grid` |
| P, T, Q sets | `engine.enumerate_conflicts`, `engine.build_instance` |
| Checker | `engine.check_plan`, `engine.check_indices` |
| Cost of a plan | `engine.cost_of`, `engine.cost_vector` |
| Brute force | `engine.brute_force` |
| Product counts, uniform-grid term counts | `engine.count_third_order_products`, `engine.uniform_grid_term_counts` |
| Tests | `tests/test_engine.py` |

## Numbers to remember

- 16 grid points, 5 mics, 4,368 possible plans.
- 792 plans meet the spacing rule. **24 are IM-free**: 0.55% of all plans, 3.0% of well-spaced ones.
- 15 pairs, 56 triples, 252 quadruples.
- 3 mics make 9 third-order products. 5 make 50. 40 make 31,200 (1,560 two-tone, 29,640 three-tone).
- Brute force over 4,368 plans takes about 10 ms.
- With an exclusion: 13 points, 1,287 plans, 8 IM-free.
- Six IM-free mics need 21 grid points, and only 2 plans work.

## Likely questions

**Why only third-order products?** They are the strongest products that land near the carriers. Fifth-order products (like 3f1 - 2f2) also land in band, and Shure's page mentions them. We left them out to keep the demo at 16 qubits. They are on our "what's next" list.

**Why 250 kHz?** Shure's guide says most manufacturers recommend at least 250 kHz between any third-order product and any carrier.

**Why 500 kHz between carriers?** It is a demo choice. It rules out neighbouring grid points. We found no source for it, so we label it as a choice.

**Why a grid at all?** Each candidate frequency becomes one qubit, so we need a finite list. The engine accepts any step, so a finer grid just means more qubits.

**What if a product lands 100 kHz from a mic?** That counts as a hit, because 100 kHz is less than the 250 kHz guard. On our 250 kHz grid that can't happen, but on a finer grid it can, and the engine checks it.

**Why does Shure say three transmitters make six products, and you say nine?** Shure counts "in-band" products for its example. Our formula counts all six two-tone and all three three-tone products, wherever they land. The two counts measure different things.

**Is the band real for the Humanities Theatre?** No. The venue pages list no frequency bands, so 470 to 474 MHz is illustrative.
