"""Core hypothesis tests for A/B experiments (user-level randomisation)."""
from dataclasses import dataclass, asdict

import numpy as np
from scipy import stats


@dataclass
class EffectResult:
    metric: str
    control_mean: float
    treatment_mean: float
    abs_diff: float
    rel_lift: float
    ci_low: float
    ci_high: float
    p_value: float
    n_control: int
    n_treatment: int
    method: str

    def to_dict(self):
        return asdict(self)

    @property
    def significant(self):
        return self.p_value < 0.05


def _result(metric, mc, mt, se, nc, nt, method, alpha=0.05):
    diff = mt - mc
    z = stats.norm.ppf(1 - alpha / 2)
    p = 2 * (1 - stats.norm.cdf(abs(diff / se))) if se > 0 else 1.0
    return EffectResult(metric, float(mc), float(mt), float(diff), float(diff / mc) if mc else np.nan,
                        float(diff - z * se), float(diff + z * se), float(p), int(nc), int(nt), method)


def two_proportion_ztest(x_c, n_c, x_t, n_t, metric="conversion", alpha=0.05):
    """Difference in proportions with an unpooled standard error for the CI."""
    pc, pt = x_c / n_c, x_t / n_t
    se = np.sqrt(pc * (1 - pc) / n_c + pt * (1 - pt) / n_t)
    return _result(metric, pc, pt, se, n_c, n_t, "two-proportion z-test", alpha)


def welch_ttest(y_c, y_t, metric="mean", alpha=0.05):
    """Difference in means with Welch (unequal-variance) standard error, normal approximation."""
    y_c, y_t = np.asarray(y_c, float), np.asarray(y_t, float)
    se = np.sqrt(y_c.var(ddof=1) / len(y_c) + y_t.var(ddof=1) / len(y_t))
    return _result(metric, y_c.mean(), y_t.mean(), se, len(y_c), len(y_t), "Welch t-test", alpha)


def ratio_delta_var(num, den):
    """Variance of sum(num)/sum(den) across users, by the delta method.

    Needed for ratio metrics like clicks per page-view where the unit of analysis (page view)
    differs from the unit of randomisation (user). Treating page views as independent
    understates the variance and inflates false positives.
    """
    num, den = np.asarray(num, float), np.asarray(den, float)
    n = len(num)
    mx, my = num.mean(), den.mean()
    vx, vy = num.var(ddof=1), den.var(ddof=1)
    cov = np.cov(num, den, ddof=1)[0, 1]
    r = mx / my
    return (vx / my**2 - 2 * r * cov / my**2 + r**2 * vy / my**2) / n


def delta_method_ratio(num_c, den_c, num_t, den_t, metric="ratio", alpha=0.05):
    rc = np.sum(num_c) / np.sum(den_c)
    rt = np.sum(num_t) / np.sum(den_t)
    se = np.sqrt(ratio_delta_var(num_c, den_c) + ratio_delta_var(num_t, den_t))
    return _result(metric, rc, rt, se, len(num_c), len(num_t), "delta method (ratio)", alpha)


def naive_ratio_test(num_c, den_c, num_t, den_t, metric="ratio", alpha=0.05):
    """The WRONG way, kept only to demonstrate the problem: treats each denominator unit as independent."""
    x_c, n_c, x_t, n_t = np.sum(num_c), np.sum(den_c), np.sum(num_t), np.sum(den_t)
    r = two_proportion_ztest(x_c, n_c, x_t, n_t, metric, alpha)
    r.method = "naive (page-view level, wrong)"
    return r


def bootstrap_diff_ci(y_c, y_t, n_boot=2000, alpha=0.05, seed=0, stat=np.mean):
    """Percentile bootstrap CI for stat(treatment) - stat(control). Robust for heavy-tailed revenue."""
    rng = np.random.default_rng(seed)
    y_c, y_t = np.asarray(y_c, float), np.asarray(y_t, float)
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        diffs[b] = stat(y_t[rng.integers(0, len(y_t), len(y_t))]) - stat(y_c[rng.integers(0, len(y_c), len(y_c))])
    return float(np.quantile(diffs, alpha / 2)), float(np.quantile(diffs, 1 - alpha / 2))


def benjamini_hochberg(p_values, q=0.05):
    """Returns (adjusted p-values, reject flags) controlling the false discovery rate at q."""
    p = np.asarray(p_values, float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out, out <= q
