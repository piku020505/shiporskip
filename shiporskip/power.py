"""Sample size and minimum detectable effect (two-sided test, equal allocation)."""
import numpy as np
from scipy.stats import norm


def n_per_arm_proportion(p0, mde_abs, alpha=0.05, power=0.8):
    p1 = p0 + mde_abs
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    pbar = (p0 + p1) / 2
    n = (za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / mde_abs**2
    return int(np.ceil(n))


def n_per_arm_mean(sd, mde_abs, alpha=0.05, power=0.8, variance_reduction=0.0):
    """variance_reduction: e.g. 0.35 if CUPED removes 35% of the variance."""
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    var = sd**2 * (1 - variance_reduction)
    return int(np.ceil(2 * var * (za + zb) ** 2 / mde_abs**2))


def mde_mean(sd, n_per_arm, alpha=0.05, power=0.8, variance_reduction=0.0):
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    return float((za + zb) * np.sqrt(2 * sd**2 * (1 - variance_reduction) / n_per_arm))
