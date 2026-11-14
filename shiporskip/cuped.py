"""CUPED: Controlled-experiment Using Pre-Experiment Data (Deng et al., Microsoft, 2013).

Y_cuped = Y - theta * (X - mean(X)),  theta = cov(X, Y) / var(X)

X is a pre-experiment covariate (e.g. sessions in the 28 days before assignment). Randomisation makes
X independent of the treatment, so the adjustment keeps the estimate unbiased while removing the part of
Y's variance that X explains (about rho^2). Lower variance means narrower CIs, i.e. the same power with fewer users.
"""
import numpy as np


def cuped_theta(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    return float(np.cov(x, y, ddof=1)[0, 1] / x.var(ddof=1))


def cuped_adjust(y, x, theta=None, x_mean=None):
    y, x = np.asarray(y, float), np.asarray(x, float)
    theta = cuped_theta(y, x) if theta is None else theta
    x_mean = x.mean() if x_mean is None else x_mean
    return y - theta * (x - x_mean), theta


def cuped_pooled(y_c, x_c, y_t, x_t):
    """Estimate theta on pooled data (both arms) and apply it to each arm with the pooled X mean."""
    y = np.concatenate([y_c, y_t]); x = np.concatenate([x_c, x_t])
    theta, xm = cuped_theta(y, x), float(np.mean(x))
    yc_adj, _ = cuped_adjust(y_c, x_c, theta, xm)
    yt_adj, _ = cuped_adjust(y_t, x_t, theta, xm)
    var_before = np.var(y_c, ddof=1) + np.var(y_t, ddof=1)
    var_after = np.var(yc_adj, ddof=1) + np.var(yt_adj, ddof=1)
    return yc_adj, yt_adj, {"theta": theta, "variance_reduction": float(1 - var_after / var_before),
                            "corr_xy": float(np.corrcoef(x, y)[0, 1])}
