"""
Prove the engine is trustworthy before trusting its verdicts.

1. A/A tests: randomly split the CONTROL users into two fake arms 1,000 times. A correct test should
   flag ~5% as significant, and p-values should be uniform.
2. Ratio metrics: same A/A splits for checkout-starts-per-pricing-view; naive page-view-level test
   vs delta method.
3. CUPED: unbiased in A/A, and how much variance it removes.
4. Peeking: false-positive rate when checking a 28-day test every day, naive vs O'Brien-Fleming.
5. Power: sample size needed for the primary metric, with and without CUPED.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shiporskip import (cuped_pooled, delta_method_ratio, n_per_arm_mean, naive_ratio_test,  # noqa: E402
                    obrien_fleming_bounds, peeking_false_positive_rate, two_proportion_ztest, welch_ttest)


def run(n_sims=1000, seed=123):
    df = pd.read_csv(ROOT / "case_study" / "data" / "pricing_test.csv.gz")
    ctrl = df[(df.variant == "control") & ~((df.platform == "android") & df.assign_day.isin([4, 5]))].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    conv, rev, ratio_naive, ratio_delta, cup_diffs, raw_diffs, vr = [], [], [], [], [], [], []
    y_c = ctrl.converted.to_numpy(); r = ctrl.revenue_12m.to_numpy(); s = ctrl.sessions.to_numpy()
    x = ctrl.pre_sessions.to_numpy(); num = ctrl.checkout_starts.to_numpy(); den = ctrl.pricing_views.to_numpy()
    for _ in range(n_sims):
        a = rng.random(len(ctrl)) < 0.5
        b = ~a
        conv.append(two_proportion_ztest(y_c[a].sum(), a.sum(), y_c[b].sum(), b.sum()).p_value)
        rev.append(welch_ttest(r[a], r[b]).p_value)
        ratio_naive.append(naive_ratio_test(num[a], den[a], num[b], den[b]).p_value)
        ratio_delta.append(delta_method_ratio(num[a], den[a], num[b], den[b]).p_value)
        ya, yb, info = cuped_pooled(s[a], x[a], s[b], x[b])
        cup_diffs.append(yb.mean() - ya.mean()); raw_diffs.append(s[b].mean() - s[a].mean())
        vr.append(info["variance_reduction"])
    fpr = lambda p: float(np.mean(np.asarray(p) < 0.05))
    looks = 28
    obf = obrien_fleming_bounds(looks)
    sd_rev = df.revenue_12m.std()
    # variance reduction CUPED achieves on the primary metric in this dataset
    vr_primary = cuped_pooled(r, x, r, x)[2]["variance_reduction"]
    res = {
        "n_aa_sims": n_sims,
        "aa_fpr_conversion": fpr(conv),
        "aa_fpr_revenue": fpr(rev),
        "aa_fpr_ratio_naive": fpr(ratio_naive),
        "aa_fpr_ratio_delta": fpr(ratio_delta),
        "cuped_mean_diff_aa": float(np.mean(cup_diffs)),
        "cuped_sd_diff_aa": float(np.std(cup_diffs)),
        "raw_sd_diff_aa": float(np.std(raw_diffs)),
        "cuped_variance_reduction_sessions": float(np.mean(vr)),
        "cuped_variance_reduction_revenue": float(vr_primary),
        "peeking_looks": looks,
        "peeking_fpr_naive": peeking_false_positive_rate(looks),
        "peeking_fpr_obrien_fleming": peeking_false_positive_rate(looks, bounds=obf),
        "obf_first_look_z": obf[0], "obf_final_look_z": obf[-1],
        "n_per_arm_rpv_mde_3pct": n_per_arm_mean(sd_rev, 0.03 * df.revenue_12m.mean()),
        "n_per_arm_sessions_mde_2pct_raw": n_per_arm_mean(df.sessions.std(), 0.02 * df.sessions.mean()),
        "n_per_arm_sessions_mde_2pct_cuped": n_per_arm_mean(df.sessions.std(), 0.02 * df.sessions.mean(),
                                                            variance_reduction=float(np.mean(vr))),
    }
    res["_pvalues"] = {"conversion": conv, "ratio_naive": ratio_naive, "ratio_delta": ratio_delta}
    return res


if __name__ == "__main__":
    out = run()
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("_")}, indent=1))
