"""Unit tests for shiporskip. Run: pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shiporskip import (analyze, benjamini_hochberg, cuped_pooled, delta_method_ratio, n_per_arm_proportion,  # noqa: E402
                    obrien_fleming_bounds, peeking_false_positive_rate, srm_test, two_proportion_ztest,
                    welch_ttest)


def test_srm_balanced_passes():
    assert not srm_test([50_120, 49_880])["srm_detected"]


def test_srm_imbalanced_flagged():
    assert srm_test([50_600, 49_400])["srm_detected"]


def test_ztest_matches_textbook_pvalue():
    r = two_proportion_ztest(500, 10_000, 560, 10_000)
    se = np.sqrt(0.05 * 0.95 / 1e4 + 0.056 * 0.944 / 1e4)
    assert r.p_value == pytest.approx(2 * (1 - sps.norm.cdf(0.006 / se)), rel=1e-9)
    assert r.ci_low < 0.006 < r.ci_high


def test_welch_matches_scipy():
    rng = np.random.default_rng(0)
    a, b = rng.normal(10, 3, 5000), rng.normal(10.2, 4, 5000)
    ours = welch_ttest(a, b).p_value
    ref = sps.ttest_ind(b, a, equal_var=False).pvalue
    assert ours == pytest.approx(ref, abs=1e-3)       # normal vs t approximation at n=5000


def test_cuped_unbiased_and_reduces_variance():
    rng = np.random.default_rng(1)
    diffs_raw, diffs_cuped = [], []
    for _ in range(300):
        x = rng.normal(0, 1, 4000)
        y = 2 * x + rng.normal(0, 1, 4000)            # corr ~0.89 → ~80% variance reduction
        y[2000:] += 0.1                               # true effect 0.1
        yc, yt, info = cuped_pooled(y[:2000], x[:2000], y[2000:], x[2000:])
        diffs_raw.append(y[2000:].mean() - y[:2000].mean()); diffs_cuped.append(yt.mean() - yc.mean())
    assert np.mean(diffs_cuped) == pytest.approx(0.1, abs=0.01)
    assert np.var(diffs_cuped) < 0.3 * np.var(diffs_raw)


def test_delta_method_coverage_with_clustered_data():
    """A/A with strongly clustered page views: delta-method CIs should cover 0 about 95% of the time."""
    rng = np.random.default_rng(2)
    cover = []
    for _ in range(400):
        views = 1 + rng.poisson(rng.lognormal(0.5, 1.0, 4000))
        clicks = rng.binomial(views, rng.beta(1, 6, 4000))
        r = delta_method_ratio(clicks[:2000], views[:2000], clicks[2000:], views[2000:])
        cover.append(r.ci_low <= 0 <= r.ci_high)
    assert 0.92 <= np.mean(cover) <= 0.98


def test_sample_size_known_value():
    # p0 = 10%, +1 pp, alpha .05, power .8 → ~14,750 per arm (standard calculators give 14,751)
    assert 14_600 <= n_per_arm_proportion(0.10, 0.01) <= 14_900


def test_benjamini_hochberg():
    adj, rej = benjamini_hochberg([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216])
    assert rej.tolist() == [True, True] + [False] * 8
    assert adj[0] == pytest.approx(0.01)


def test_obf_single_look_is_196():
    assert obrien_fleming_bounds(1, n_sims=400_000)[0] == pytest.approx(1.96, abs=0.02)


def test_peeking_inflates_and_obf_controls():
    naive = peeking_false_positive_rate(10, n_sims=20_000)
    seq = peeking_false_positive_rate(10, n_sims=20_000, bounds=obrien_fleming_bounds(10))
    assert naive > 0.15
    assert seq == pytest.approx(0.05, abs=0.01)


def _toy(n=40_000, effect=0.0, seed=3):
    rng = np.random.default_rng(seed)
    v = np.where(rng.random(n) < 0.5, "treatment", "control")
    conv = (rng.random(n) < 0.05 + effect * (v == "treatment")).astype(int)
    return pd.DataFrame({"variant": v, "converted": conv, "rev": conv * 100.0, "pre": rng.poisson(2, n),
                         "seg": rng.choice(["a", "b"], n), "day": rng.integers(1, 8, n)})


CFG = {"name": "toy", "primary": {"name": "rev", "type": "mean", "col": "rev", "cuped_covariate": "pre"},
       "guardrails": [{"name": "conv", "type": "proportion", "col": "converted", "max_decrease_rel": 0.2}],
       "segments": ["seg"], "srm_drilldown": ["day"]}


def test_analyze_ships_clear_winner():
    assert analyze(_toy(effect=0.01), CFG)["decision"].startswith("SHIP")


def test_analyze_blocks_on_srm():
    d = _toy()
    d = d.drop(d[(d.variant == "treatment") & (d.day == 3)].sample(frac=0.6, random_state=0).index)
    res = analyze(d, CFG)
    assert res["decision"].startswith("INVALID")
    assert res["srm_drilldown"][0]["value"] == 3          # drill-down points at the broken day


def test_analyze_no_decision_on_null():
    assert analyze(_toy(effect=0.0, seed=5), CFG)["decision"].startswith("NO DECISION")
