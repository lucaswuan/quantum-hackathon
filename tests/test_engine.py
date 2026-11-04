import pytest

from micplanner.engine import (brute_force, build_instance, check_indices, check_plan, cost_of,
                               count_third_order_products, parse_freq, parse_range)

MHZ = 1_000_000


@pytest.fixture(scope="module")
def demo():
    return build_instance("470-474 MHz", mics=5, step="250 kHz", spacing="500 kHz", im_guard="250 kHz")


def test_parsing():
    assert parse_freq("250 kHz") == 250_000
    assert parse_freq("472.5 MHz") == 472_500_000
    assert parse_freq("0.25MHz") == 250_000
    assert parse_range("470-474 MHz") == (470 * MHZ, 474 * MHZ)
    assert parse_range("470 MHz to 474 MHz") == (470 * MHZ, 474 * MHZ)
    assert parse_range("472.0-472.5 MHz") == (472 * MHZ, 472_500_000)
    with pytest.raises(ValueError):
        parse_range("474-470 MHz")


def test_grid_is_16_points_with_top_edge_excluded(demo):
    assert demo.n_points == 16
    assert demo.freqs[0] == 470 * MHZ
    assert demo.freqs[-1] == 473_750_000


def test_exclusion_drops_three_points():
    inst = build_instance("470-474 MHz", mics=5, exclude=["472.0-472.5 MHz"])
    assert inst.n_points == 13
    assert 472 * MHZ not in inst.freqs and 472_500_000 not in inst.freqs


def test_term_counts(demo):
    assert (len(demo.pairs), len(demo.triples), len(demo.quads)) == (15, 56, 252)


def test_brute_force_matches_expected_check(demo):
    bf = brute_force(demo)
    assert bf.n_plans == 4368
    assert bf.n_spaced == 792
    assert bf.n_clean == 24
    assert bf.best_cost == 0
    assert (0, 2, 5, 9, 15) in bf.best_plans


def test_inclusive_guard_leaves_no_clean_plan():
    # Counting products exactly 250 kHz away is the same as a guard of 250 kHz + 1 Hz.
    inst = build_instance("470-474 MHz", mics=5, im_guard="250.001 kHz")
    assert brute_force(inst).n_clean == 0


def test_evenly_spaced_plan_is_full_of_hits(demo):
    plan = (0, 3, 6, 9, 12)
    res = check_indices(demo, plan)
    assert res.counts == {"spacing": 0, "two-tone": 8, "three-tone": 12}
    assert cost_of(demo, plan) == 4 + 3


def test_checker_on_raw_frequencies():
    res = check_plan([470_000_000, 470_500_000, 471_000_000], 500_000, 250_000)
    # 2 x 470.5 - 470.0 = 471.0 and 2 x 470.5 - 471.0 = 470.0
    assert res.counts["two-tone"] == 2
    assert check_plan([470_000_000, 470_500_000, 471_250_000], 500_000, 250_000).clean


def test_uniform_grid_formula_matches_enumeration():
    from micplanner.engine import uniform_grid_term_counts
    for N in (5, 9, 16):
        inst = build_instance(f"470-{470 + N * 0.25} MHz", mics=2)
        assert inst.n_points == N
        assert uniform_grid_term_counts(N) == (len(inst.triples), len(inst.quads))


def test_product_counts():
    assert count_third_order_products(40) == {"two-tone": 1560, "three-tone": 29640, "total": 31200}
    assert count_third_order_products(3)["total"] == 9
