"""Peeking and group-sequential boundaries.

Checking a fixed-horizon test every day and stopping at the first p < 0.05 inflates the false-positive
rate far above 5%. An O'Brien-Fleming-style boundary demands very strong evidence early and close to
the usual 1.96 at the final look, which keeps the overall error rate at alpha.
"""
import numpy as np


def _null_z_paths(n_looks, n_sims, rng):
    """Z-statistics at each of K equally spaced looks under H0 (cumulative sums of N(0,1) increments)."""
    inc = rng.standard_normal((n_sims, n_looks))
    return np.cumsum(inc, axis=1) / np.sqrt(np.arange(1, n_looks + 1))


def obrien_fleming_bounds(n_looks, alpha=0.05, n_sims=200_000, seed=7):
    """Boundaries c * sqrt(K / k), with c calibrated by simulation so P(cross at any look | H0) = alpha."""
    rng = np.random.default_rng(seed)
    z = np.abs(_null_z_paths(n_looks, n_sims, rng))
    shape = np.sqrt(n_looks / np.arange(1, n_looks + 1))
    lo, hi = 1.0, 6.0
    for _ in range(60):                                  # bisection on c
        c = (lo + hi) / 2
        fpr = np.mean(np.any(z > c * shape, axis=1))
        lo, hi = (c, hi) if fpr > alpha else (lo, c)
    return (hi * shape).tolist()


def peeking_false_positive_rate(n_looks, alpha=0.05, n_sims=20_000, seed=11, bounds=None):
    """Share of A/A tests declared 'significant' at ANY look, with a naive or sequential boundary."""
    from scipy.stats import norm
    rng = np.random.default_rng(seed)
    z = np.abs(_null_z_paths(n_looks, n_sims, rng))
    b = np.full(n_looks, norm.ppf(1 - alpha / 2)) if bounds is None else np.asarray(bounds)
    return float(np.mean(np.any(z > b, axis=1)))
