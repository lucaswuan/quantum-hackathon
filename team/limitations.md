# Limitations

An honest list. Say these before a judge does.

## About the claim

- **No speed-up.** QAOA is a heuristic with no proven advantage here. Brute force, greedy, simulated annealing and an integer program all solve the demo in well under a second.
- **A modest gain over random.** At p = 3, 7.1% of samples are IM-free against 0.55% for random plans. That is about 13 times better, but far from always finding a clean plan.
- **Angles tuned by exact classical simulation.** This only works because the demo is small. At large sizes the angles would have to be tuned on hardware or by other methods.
- **p = 4 and 5 results (10% and 12%) are from the fast simulation only.** They were not run through the circuit sampler.
- **"No earlier quantum approach" rests on our own search.** We checked D-Wave's frequency-selection example, Vandelli et al. 2025 and GitHub, and found none that models IM. We can't rule out work we didn't find.

## About the model

- **Third-order products only.** No fifth-order products, which Shure's page also lists as in-band.
- **All carriers treated alike.** We ignore transmitter power, distance between transmitters, antenna placement and receiver selectivity, which decide how strong a product really is.
- **A uniform 250 kHz grid.** On this grid the 250 kHz guard just means "lands exactly on a mic", so the demo is a Golomb-ruler search with no gap of 1 (Babcock 1953). Finer grids break that link but cost more qubits.
- **The 500 kHz carrier spacing is our choice**, not a vendor rule.
- **No TV channel data, no scan data, no licensing rules.** The band and the exclusion are illustrative.
- **The venue facts are thin.** The Humanities Theatre's spec sheet lists six Shure ULD channels but no frequency bands or receiver models.

## About the circuit

- **Deep.** 12,716 CNOTs at p = 3 (4,006 per cost layer as `qaoa_ansatz` builds it). Not run on hardware. We expect noise to dominate at this depth on current devices.
- **All-to-all connectivity assumed.** Real devices would add SWAPs for routing.
- **Scaling is steep.** 40 IM-free mics on this kind of grid need at least 782 qubits and about 39.6 million four-qubit terms.

## About the tool

- **Simulator only, up to 20 grid points.** `plan_mics` refuses bigger grids.
- **Not for real shows.** Use the vendors' own software, such as Shure's free Wireless Workbench, for real coordination.
