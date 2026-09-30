"""The statistics against published reference values."""
import pytest

import stats


def test_wilson_reference_values():
    lo, hi = stats.wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4)
    assert hi == pytest.approx(0.7634, abs=1e-4)
    lo, hi = stats.wilson(0, 10)
    assert lo == 0.0
    assert hi == pytest.approx(0.2775, abs=1e-4)
    assert stats.wilson(0, 0) is None


def test_newcombe_reference_example():
    # Newcombe (1998), example (a): 56 of 70 against 48 of 80, difference 0.2000,
    # hybrid score interval 0.0524 to 0.3339.
    d, (lo, hi) = stats.newcombe(48, 80, 56, 70)
    assert d == pytest.approx(0.2)
    assert lo == pytest.approx(0.0524, abs=1e-4)
    assert hi == pytest.approx(0.3339, abs=1e-4)


def test_poisson_exact_reference_values():
    assert stats.poisson_exact(0) == pytest.approx((0.0, 3.6889), abs=1e-4)
    lo, hi = stats.poisson_exact(1)
    assert lo == pytest.approx(0.0253, abs=1e-4)
    assert hi == pytest.approx(5.5716, abs=1e-4)
    rate, (rlo, rhi) = stats.rate_per(1, 50)
    assert rate == pytest.approx(2.0)
    assert rhi == pytest.approx(5.5716 * 2, abs=1e-3)
    assert stats.rate_per(3, 0) is None


def test_kappa_reference_value():
    # 2x2 table 20, 5 / 10, 15: po = 0.7, pe = 0.5, kappa = 0.4.
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert stats.cohen_kappa(a, b) == pytest.approx(0.4)
    assert stats.cohen_kappa(["y", "y"], ["y", "y"]) is None


def test_kappa_bootstrap_is_seeded_and_brackets_the_point():
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    k1, ci1 = stats.kappa_bootstrap(a, b)
    k2, ci2 = stats.kappa_bootstrap(a, b)
    assert (k1, ci1) == (k2, ci2)
    assert ci1[0] < k1 < ci1[1]


def test_cluster_bootstrap_is_seeded_and_resamples_cases():
    pt, ci = stats.cluster_bootstrap([0.2, 0.9, 1.0, 0.8, 1.0])
    assert pt == pytest.approx(0.78)
    assert (pt, ci) == stats.cluster_bootstrap([0.2, 0.9, 1.0, 0.8, 1.0])
    assert ci[0] >= 0.2 and ci[1] <= 1.0 and ci[0] < pt < ci[1]
    assert stats.cluster_bootstrap([0.5, 0.5, 0.5]) == (0.5, (0.5, 0.5))
