"""Config-driven experiment analysis: SRM gate → metrics (with CUPED / delta method) → guardrails →
segments (with FDR control) → decision."""
import numpy as np
import pandas as pd

from .cuped import cuped_pooled
from .srm import srm_drilldown, srm_test
from .stats import (benjamini_hochberg, bootstrap_diff_ci, delta_method_ratio, two_proportion_ztest,
                    welch_ttest)


def _metric(df_c, df_t, m):
    t = m["type"]
    if t == "proportion":
        r = two_proportion_ztest(df_c[m["col"]].sum(), len(df_c), df_t[m["col"]].sum(), len(df_t), m["name"])
        extra = {}
    elif t == "mean":
        yc, yt = df_c[m["col"]].to_numpy(float), df_t[m["col"]].to_numpy(float)
        r = welch_ttest(yc, yt, m["name"])
        extra = {}
        if m.get("cuped_covariate"):
            cov = m["cuped_covariate"]
            yc_a, yt_a, info = cuped_pooled(yc, df_c[cov].to_numpy(float), yt, df_t[cov].to_numpy(float))
            ra = welch_ttest(yc_a, yt_a, m["name"])
            # report raw arm means but CUPED difference / CI / p-value
            extra = {"raw_ci": [r.ci_low, r.ci_high], "raw_p_value": r.p_value, **{f"cuped_{k}": v for k, v in info.items()},
                     "ci_width_reduction": 1 - (ra.ci_high - ra.ci_low) / (r.ci_high - r.ci_low)}
            r.abs_diff, r.ci_low, r.ci_high, r.p_value = ra.abs_diff, ra.ci_low, ra.ci_high, ra.p_value
            r.rel_lift = ra.abs_diff / r.control_mean
            r.method = "Welch t-test + CUPED"
        if m.get("bootstrap"):
            extra["bootstrap_ci_raw"] = bootstrap_diff_ci(yc, yt, n_boot=m.get("n_boot", 1000))
    elif t == "ratio":
        r = delta_method_ratio(df_c[m["num"]], df_c[m["den"]], df_t[m["num"]], df_t[m["den"]], m["name"])
        extra = {}
    else:
        raise ValueError(f"unknown metric type {t}")
    out = r.to_dict()
    out.update(extra)
    return out


def _guardrail_check(res, g):
    """Non-inferiority style: the worst plausible value (CI bound) must stay inside the allowed margin."""
    if "max_increase_abs" in g:                       # e.g. refund rate must not rise by > 1 pp
        ok = res["ci_high"] <= g["max_increase_abs"]
        rule = f"increase ≤ {g['max_increase_abs']:+.4f} (CI upper {res['ci_high']:+.4f})"
    elif "max_decrease_rel" in g:                     # e.g. conversion must not fall by > 5% relative
        floor = -g["max_decrease_rel"] * res["control_mean"]
        ok = res["ci_low"] >= floor
        rule = f"decrease ≥ {-g['max_decrease_rel']:.0%} rel (CI lower {res['ci_low'] / res['control_mean']:+.1%} rel)"
    else:
        raise ValueError("guardrail needs max_increase_abs or max_decrease_rel")
    point_ok = (res["abs_diff"] <= g.get("max_increase_abs", np.inf)) and \
               (res["abs_diff"] >= -g.get("max_decrease_rel", np.inf) * res["control_mean"])
    status = "PASS" if ok else ("AT RISK" if point_ok else "FAIL")
    return {**res, "guardrail_rule": rule, "status": status}


def analyze(df, cfg, exclude=None):
    vc, ctl, trt = cfg.get("variant_col", "variant"), cfg.get("control", "control"), cfg.get("treatment", "treatment")
    out = {"experiment": cfg["name"], "n_rows_raw": int(len(df))}

    # ---------- 1. SRM gate ----------
    counts = df[vc].value_counts().reindex([ctl, trt]).fillna(0).to_numpy()
    out["srm"] = srm_test(counts, cfg.get("expected_split", [0.5, 0.5]))
    if out["srm"]["srm_detected"]:
        out["srm_drilldown"] = srm_drilldown(df, vc, cfg.get("srm_drilldown", [])).head(8).to_dict("records")
    if exclude is not None:
        df = df[~exclude(df)].copy()
        counts = df[vc].value_counts().reindex([ctl, trt]).fillna(0).to_numpy()
        out["srm_after_exclusion"] = srm_test(counts, cfg.get("expected_split", [0.5, 0.5]))
        out["exclusion_rule"] = cfg.get("exclusion_note", "custom exclusion")
    valid = not (out.get("srm_after_exclusion", out["srm"])["srm_detected"])
    out["valid"] = valid
    out["n_analyzed"] = int(len(df))

    c, t = df[df[vc] == ctl], df[df[vc] == trt]

    # ---------- 2. metrics ----------
    out["primary"] = _metric(c, t, cfg["primary"])
    out["secondary"] = [_metric(c, t, m) for m in cfg.get("secondary", [])]
    out["guardrails"] = [_guardrail_check(_metric(c, t, g), g) for g in cfg.get("guardrails", [])]

    # ---------- 3. segments (primary + segment metrics), FDR-controlled ----------
    seg_rows = []
    for dim in cfg.get("segments", []):
        for val, g in df.groupby(dim):
            gc, gt = g[g[vc] == ctl], g[g[vc] == trt]
            for m in [cfg["primary"]] + cfg.get("segment_metrics", []):
                m2 = {k: v for k, v in m.items() if k not in ("cuped_covariate", "bootstrap")}
                r = _metric(gc, gt, m2)
                seg_rows.append({"dimension": dim, "segment": str(val), **{k: r[k] for k in
                                 ["metric", "control_mean", "treatment_mean", "abs_diff", "rel_lift",
                                  "ci_low", "ci_high", "p_value", "n_control", "n_treatment"]}})
    seg = pd.DataFrame(seg_rows)
    if len(seg):
        seg["p_adj_bh"], seg["significant_after_fdr"] = benjamini_hochberg(seg.p_value.to_numpy())
    out["segments"] = seg.to_dict("records")

    # ---------- 4. decision ----------
    p = out["primary"]
    gr = [g["status"] for g in out["guardrails"]]
    if not valid:
        decision = "INVALID - sample ratio mismatch; fix assignment/logging before reading results"
    elif p["p_value"] < 0.05 and p["abs_diff"] > 0:
        if all(s == "PASS" for s in gr):
            decision = "SHIP - primary metric improved and all guardrails passed"
        elif any(s == "FAIL" for s in gr):
            decision = "DO NOT SHIP AS IS - primary improved but a guardrail failed"
        else:
            decision = "SHIP WITH CONDITIONS - primary improved; a guardrail cannot yet rule out harm"
    elif p["p_value"] < 0.05 and p["abs_diff"] < 0:
        decision = "DO NOT SHIP - primary metric got worse"
    else:
        decision = "NO DECISION - primary effect not distinguishable from zero; keep control or extend"
    out["decision"] = decision
    return out
