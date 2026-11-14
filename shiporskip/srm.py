"""Sample Ratio Mismatch (SRM) detection.

If a 50/50 test ends up 50.6/49.4 with 100K users, something in assignment or logging is broken,
and every metric comparison is suspect. Check this BEFORE looking at any outcome metric.
"""
import numpy as np
import pandas as pd
from scipy import stats

SRM_ALPHA = 0.001          # industry convention: very strict, because SRM invalidates the test


def srm_test(counts, expected_ratios=None):
    counts = np.asarray(counts, float)
    if expected_ratios is None:
        expected_ratios = np.ones(len(counts)) / len(counts)
    expected = counts.sum() * np.asarray(expected_ratios, float)
    chi2, p = stats.chisquare(counts, expected)
    return {"counts": counts.astype(int).tolist(), "expected": expected.round(1).tolist(),
            "observed_share_treatment": float(counts[-1] / counts.sum()),
            "chi2": float(chi2), "p_value": float(p), "srm_detected": bool(p < SRM_ALPHA)}


def srm_drilldown(df, variant_col="variant", by=("platform", "assign_day")):
    """Run the SRM test inside each slice so the broken slice can be located."""
    rows = []
    for col in by:
        for val, g in df.groupby(col):
            c = g[variant_col].value_counts().reindex(["control", "treatment"]).fillna(0).to_numpy()
            if c.sum() < 100:
                continue
            r = srm_test(c)
            rows.append({"dimension": col, "value": val, "n_control": int(c[0]), "n_treatment": int(c[1]),
                         "share_treatment": round(r["observed_share_treatment"], 4),
                         "p_value": r["p_value"], "srm_detected": r["srm_detected"]})
    return pd.DataFrame(rows).sort_values("p_value")
