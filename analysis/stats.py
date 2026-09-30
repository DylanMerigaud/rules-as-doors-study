"""Statistics of the study (PREREG.md section 10), with no dependency beyond numpy and scipy.

- Proportions: Wilson 95% intervals.
- Difference of two independent proportions: Newcombe's hybrid score interval (method 10).
- Rates: counts over exposure with an exact Poisson interval.
- Clustered E1 values: a percentile cluster bootstrap over cases, 10,000 resamples,
  numpy default_rng(20260930). Every call starts a fresh generator from the seed, so a number
  does not depend on the order in which the scripts run.
- Agreement: Cohen's kappa with a bootstrap interval over items (same resamples and seed).
"""
import math

import numpy as np
from scipy.stats import chi2

SEED = 20260930
RESAMPLES = 10000
Z95 = 1.959963984540054


def wilson(k, n, z=Z95):
    """Wilson score interval for k successes out of n. None when n is 0."""
    if n <= 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(k1, n1, k2, n2):
    """Difference p2 minus p1 with Newcombe's hybrid score interval. None if a group is empty."""
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return d, (lo, hi)


def poisson_exact(k, alpha=0.05):
    """Exact (Garwood) interval for a Poisson count k."""
    lo = 0.0 if k == 0 else chi2.ppf(alpha / 2, 2 * k) / 2
    hi = chi2.ppf(1 - alpha / 2, 2 * k + 2) / 2
    return float(lo), float(hi)


def rate_per(k, exposure, per=100.0):
    """Rate of k events per `per` units of exposure, with its exact Poisson interval."""
    if exposure <= 0:
        return None
    lo, hi = poisson_exact(k)
    return k / exposure * per, (lo / exposure * per, hi / exposure * per)


def percentile_interval(samples):
    lo, hi = np.quantile(np.asarray(samples, dtype=float), [0.025, 0.975])
    return float(lo), float(hi)


def cluster_bootstrap(per_case, resamples=RESAMPLES, seed=SEED):
    """Unweighted mean of per-case values with the percentile interval of a bootstrap that
    resamples the cases with replacement (PREREG.md section 8). Returns (point, (lo, hi))."""
    arr = np.asarray(per_case, dtype=float)
    n = arr.shape[0]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(resamples, n))
    boot = arr[idx].mean(axis=1)
    return float(arr.mean()), percentile_interval(boot)


def cohen_kappa(a, b):
    """Cohen's kappa of two equal-length label sequences. None when undefined."""
    a, b = list(a), list(b)
    n = len(a)
    if n == 0 or n != len(b):
        return None
    labels = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in labels)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def kappa_bootstrap(a, b, resamples=RESAMPLES, seed=SEED):
    """Kappa with a percentile bootstrap interval over items. Resamples where kappa is undefined
    (a single label on both sides) are left out of the interval."""
    a, b = list(a), list(b)
    k = cohen_kappa(a, b)
    if k is None:
        return None
    n = len(a)
    labels = sorted(set(a) | set(b))
    code = {c: i for i, c in enumerate(labels)}
    ai = np.array([code[x] for x in a])
    bi = np.array([code[x] for x in b])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(resamples, n))
    A, B = ai[idx], bi[idx]
    po = (A == B).mean(axis=1)
    pe = np.zeros(resamples)
    for c in range(len(labels)):
        pe += (A == c).mean(axis=1) * (B == c).mean(axis=1)
    ok = pe < 1.0
    ks = (po[ok] - pe[ok]) / (1 - pe[ok])
    return k, percentile_interval(ks)
