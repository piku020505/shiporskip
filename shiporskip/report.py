"""Render an analysis result (from shiporskip.analyze) as a Markdown decision memo."""


def _fmt(v, kind):
    if kind == "pct":
        return f"{v:.2%}"
    if kind == "pp":
        return f"{v * 100:+.2f} pp"
    if kind == "inr":
        return f"₹{v:,.2f}"
    return f"{v:.4f}"


def _p(p):
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def _kind(name, value):
    if any(k in name for k in ("conversion", "share", "rate")):
        return "pct", "pp"
    if "revenue" in name:
        return "inr", "inr"
    return "num", "num"


def _row(r):
    k, dk = _kind(r["metric"], r["control_mean"])
    diff = _fmt(r["abs_diff"], dk) if dk != "inr" else f"{r['abs_diff']:+,.2f}"
    ci = (f"[{_fmt(r['ci_low'], dk)}, {_fmt(r['ci_high'], dk)}]" if dk == "pp"
          else f"[{r['ci_low']:+,.3f}, {r['ci_high']:+,.3f}]")
    return (f"| {r['metric']} | {_fmt(r['control_mean'], k)} | {_fmt(r['treatment_mean'], k)} | {diff} "
            f"| {r['rel_lift']:+.1%} | {ci} | {_p(r['p_value'])} | {r['method']} |")


def render_markdown(res):
    L = [f"# Decision memo: {res['experiment']}", "", f"## Decision: **{res['decision']}**", ""]
    s = res["srm"]
    L += ["## 1. Data-quality gate (sample ratio mismatch)",
          f"- Raw split: control {s['counts'][0]:,} vs treatment {s['counts'][1]:,} "
          f"(treatment share {s['observed_share_treatment']:.2%}); χ² p = {s['p_value']:.2e} → "
          f"**{'SRM DETECTED' if s['srm_detected'] else 'no SRM'}** (threshold p < 0.001)"]
    if res.get("srm_drilldown"):
        L += ["", "| dimension | value | control | treatment | treatment share | p |", "|---|---|---|---|---|---|"]
        for d in res["srm_drilldown"][:5]:
            L.append(f"| {d['dimension']} | {d['value']} | {d['n_control']:,} | {d['n_treatment']:,} "
                     f"| {d['share_treatment']:.2%} | {d['p_value']:.1e} |")
    if res.get("srm_after_exclusion"):
        a = res["srm_after_exclusion"]
        L += ["", f"- Exclusion applied: {res['exclusion_rule']}.",
              f"- After exclusion: treatment share {a['observed_share_treatment']:.2%}, p = {a['p_value']:.3f} → "
              f"**{'still SRM' if a['srm_detected'] else 'clean'}**. Analysed {res['n_analyzed']:,} of {res['n_rows_raw']:,} visitors."]
    hdr = ["| metric | control | treatment | diff | rel. lift | 95% CI (diff) | p | method |",
           "|---|---|---|---|---|---|---|---|"]
    L += ["", "## 2. Primary metric"] + hdr + [_row(res["primary"])]
    p = res["primary"]
    if "cuped_variance_reduction" in p:
        L.append(f"\nCUPED (pre-period sessions) removed {p['cuped_variance_reduction']:.1%} of variance "
                 f"(raw p = {_p(p['raw_p_value'])}).")
    if "bootstrap_ci_raw" in p:
        b = p["bootstrap_ci_raw"]
        L.append(f"Bootstrap 95% CI on the raw difference: [{b[0]:+.2f}, {b[1]:+.2f}].")
    L += ["", "## 3. Secondary metrics"] + hdr + [_row(r) for r in res["secondary"]]
    L += ["", "## 4. Guardrails (non-inferiority: the worst plausible value must stay inside the margin)",
          "| guardrail | rule | status |", "|---|---|---|"]
    L += [f"| {g['metric']} | {g['guardrail_rule']} | **{g['status']}** |" for g in res["guardrails"]]
    L += ["", "## 5. Segments (Benjamini-Hochberg FDR 5% across all segment tests)",
          "| dimension | segment | metric | rel. lift | p | p (BH) | significant |", "|---|---|---|---|---|---|---|"]
    L += [f"| {r['dimension']} | {r['segment']} | {r['metric']} | {r['rel_lift']:+.1%} | {r['p_value']:.4f} "
          f"| {r['p_adj_bh']:.4f} | {'✅' if r['significant_after_fdr'] else ''} |" for r in res["segments"]]
    L += ["", "_Segment results are exploratory. A segment-specific launch should be confirmed with a follow-up test._"]
    return "\n".join(L) + "\n"
