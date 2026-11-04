import numpy as np
import pytest

from micplanner.cost import (check_diagonal, cost_operator, hubo_terms, naive_cnot_count, pauli_diagonal,
                             quadratize_greedy, qubo_size, z_strings_by_weight)
from micplanner.engine import build_instance, cost_vector


@pytest.fixture(scope="module")
def demo():
    return build_instance("470-474 MHz", mics=5)


def test_small_operator_diagonal_matches_cost_everywhere():
    for band, mics in (("470-472.5 MHz", 3), ("470-473 MHz", 4)):
        inst = build_instance(band, mics=mics)
        assert inst.n_points <= 12
        op = cost_operator(inst)
        assert check_diagonal(inst, op)["max_error"] < 1e-9


def test_demo_operator(demo):
    op = cost_operator(demo)
    assert op.num_qubits == 16
    assert z_strings_by_weight(op) == {1: 16, 2: 120, 3: 560, 4: 252}
    assert naive_cnot_count(op) == 3992
    res = check_diagonal(demo, op, n_spot=16)
    assert res["max_error"] < 1e-9


def test_w3_changes_weights_not_the_clean_plans(demo):
    for w3 in (0.5, 2.0):
        op = cost_operator(demo, w3)
        masks = np.array([sum(1 << i for i in p) for p in [(0, 2, 5, 9, 15), (0, 3, 6, 9, 12)]])
        d = pauli_diagonal(op, masks)
        assert d[0] == pytest.approx(0)
        assert d[1] == pytest.approx(7 * w3)
        assert np.allclose(d, cost_vector(demo, masks, w3))


def test_quadratization(demo):
    aux, subs = quadratize_greedy(demo.terms(), demo.n_points)
    assert aux == 105
    # Every substitution removes a pair from at least one high-degree term.
    assert all(count >= 1 for _, _, count in subs)
    size = qubo_size(demo, trials=20)
    assert size["variables"] == 121
    assert size["best_variables"] <= 121 <= size["worst_variables"]


def test_cubic_term_needs_one_aux():
    aux, _ = quadratize_greedy([(0, 1, 2)], 3)
    assert aux == 1
    aux, _ = quadratize_greedy([(0, 1, 2, 3)], 4)
    assert aux == 2
    # Four points 250 kHz apart: three close pairs, two evenly spaced triples, one equal-sum quadruple.
    assert hubo_terms(build_instance("470-471 MHz", mics=2)) == {
        (0, 1): 1.0, (1, 2): 1.0, (2, 3): 1.0, (0, 1, 2): 1.0, (1, 2, 3): 1.0, (0, 1, 2, 3): 1.0}
