"""
Full case study: generate data → SRM investigation → engine analysis → validation → charts + memo.
Run from the project root:  python case_study/run_case_study.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "case_study"))
from shiporskip import analyze, obrien_fleming_bounds  # noqa: E402
from shiporskip.report import render_markdown  # noqa: E402
import generate_experiment  # noqa: E402
import validate_engine  # noqa: E402

OUT = ROOT / "outputs"; CH = OUT / "charts"; CH.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titleweight": "bold"})
INK, ACCENT, MUTED, BAD, GOOD = "#1f2937", "#2563eb", "#9ca3af", "#dc2626", "#16a34a"


def exclude_bug(d):
    return (d.platform == "android") & d.assign_day.isin([4, 5])


def main():
    data = ROOT / "case_study" / "data" / "pricing_test.csv.gz"
    if not data.exists():
        data.parent.mkdir(exist_ok=True)
        generate_experiment.simulate().to_csv(data, index=False)
    df = pd.read_csv(data)
    cfg = json.loads((ROOT / "case_study" / "config.json").read_text())

    raw = analyze(df, cfg)                               # step 1: engine refuses to read results
    res = analyze(df, cfg, exclude=exclude_bug)          # step 2: after excluding the broken slice
    val = validate_engine.run()

    # ---------------- chart 1: SRM by day ----------------
    by_day = df.groupby(["assign_day", "variant"]).size().unstack()
    share = by_day["treatment"] / by_day.sum(axis=1)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.axhline(0.5, color=INK, lw=0.8, ls="--")
    ax.plot(share.index, share * 100, "-o", color=ACCENT, ms=4)
    for d in (4, 5):
        ax.plot(d, share[d] * 100, "o", color=BAD, ms=8)
    ax.annotate("Android build 7.4.1 dropped\ntreatment exposure events", (5, share[5] * 100), (9, 42.5),
                arrowprops=dict(arrowstyle="->", color=BAD), color=BAD, fontsize=8)
    ax.set_ylim(40, 53); ax.set_xlabel("assignment day"); ax.set_ylabel("% of users in treatment")
    ax.set_title(f"Sample ratio mismatch caught (overall χ² p = {raw['srm']['p_value']:.1e})")
    fig.tight_layout(); fig.savefig(CH / "01_srm_by_day.png"); plt.close(fig)

    # ---------------- chart 2: metric forest (relative lift) ----------------
    rows = [("PRIMARY: 12-month revenue / visitor", res["primary"])]
    rows += [(m["metric"].replace("_", " "), m) for m in res["secondary"]]
    rows += [("GUARDRAIL: " + g["metric"].replace("_", " "), g) for g in res["guardrails"][1:]]
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, (lab, m) in enumerate(rows[::-1]):
        lo, hi, pt = m["ci_low"] / m["control_mean"], m["ci_high"] / m["control_mean"], m["rel_lift"]
        col = GOOD if lo > 0 else (BAD if hi < 0 else MUTED)
        ax.plot([lo * 100, hi * 100], [i, i], color=col, lw=2.5); ax.plot(pt * 100, i, "o", color=col)
        ax.text(max(hi * 100, 0) + 2, i, f"{pt:+.1%}", va="center", fontsize=8)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], fontsize=8)
    ax.set_xlabel("relative change vs control, % (95% CI)"); ax.set_xlim(-25, 95)
    ax.set_title("Treatment effect on every metric")
    fig.tight_layout(); fig.savefig(CH / "02_metric_forest.png"); plt.close(fig)

    # ---------------- chart 3: tier segments ----------------
    seg = pd.DataFrame(res["segments"])
    t = seg[seg.dimension == "city_tier"]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3), sharey=True)
    for ax, met, title in zip(axes, ["projected_12m_revenue_per_visitor", "paid_conversion"],
                              ["12-month revenue / visitor", "paid conversion"]):
        s = t[t.metric == met]
        for i, r in enumerate(s.itertuples()):
            lo, hi = r.ci_low / r.control_mean * 100, r.ci_high / r.control_mean * 100
            col = GOOD if lo > 0 else (BAD if hi < 0 else MUTED)
            ax.plot([lo, hi], [i, i], color=col, lw=3); ax.plot(r.rel_lift * 100, i, "o", color=col)
            ax.text(hi + 1, i, f"{r.rel_lift:+.1%}" + (" *" if r.significant_after_fdr else ""), va="center", fontsize=8)
        ax.axvline(0, color=INK, lw=0.8); ax.set_title(title, fontsize=9)
        ax.set_yticks(range(3), ["Tier 1", "Tier 2", "Tier 3"]); ax.set_xlim(-30, 35)
        ax.set_xlabel("relative lift, %")
    fig.suptitle("Tier-3 cities are hurt by the annual default (* = significant after BH-FDR)", fontweight="bold", fontsize=10)
    fig.tight_layout(); fig.savefig(CH / "03_tier_segments.png"); plt.close(fig)

    # ---------------- chart 4: A/A p-value distribution, ratio metric ----------------
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3), sharey=True)
    for ax, key, title in zip(axes, ["ratio_naive", "ratio_delta"],
                              ["naive (page-view level)", "delta method (user level)"]):
        p = np.asarray(val["_pvalues"][key])
        ax.hist(p, bins=20, range=(0, 1), color=BAD if key == "ratio_naive" else ACCENT)
        ax.axhline(len(p) / 20, color=INK, ls="--", lw=0.8)
        ax.set_title(f"{title}: FPR {np.mean(p < 0.05):.1%}", fontsize=9); ax.set_xlabel("p-value")
    fig.suptitle(f"{val['n_aa_sims']:,} A/A tests on checkout starts per pricing view (should be flat, 5% FPR)",
                 fontweight="bold", fontsize=10)
    fig.tight_layout(); fig.savefig(CH / "04_aa_ratio_metric.png"); plt.close(fig)

    # ---------------- chart 5: peeking ----------------
    looks = val["peeking_looks"]; b = obrien_fleming_bounds(looks)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3), gridspec_kw={"width_ratios": [1, 1.4]})
    axes[0].bar(["daily peeking\n(z > 1.96)", "O'Brien-Fleming\nboundary"],
                [val["peeking_fpr_naive"] * 100, val["peeking_fpr_obrien_fleming"] * 100], color=[BAD, ACCENT])
    axes[0].axhline(5, color=INK, ls="--", lw=0.8)
    for i, v in enumerate([val["peeking_fpr_naive"], val["peeking_fpr_obrien_fleming"]]):
        axes[0].text(i, v * 100 + 0.8, f"{v:.1%}", ha="center", fontsize=9)
    axes[0].set_ylim(0, 33); axes[0].set_ylabel("false-positive rate, %"); axes[0].set_title("A/A false positives", fontsize=9)
    axes[1].plot(range(1, looks + 1), b, color=ACCENT, label="O'Brien-Fleming")
    axes[1].axhline(1.96, color=BAD, ls="--", label="naive 1.96")
    axes[1].set_ylim(0, 8); axes[1].set_xlabel("day (look)"); axes[1].set_ylabel("|z| needed to stop")
    axes[1].legend(frameon=False, fontsize=8); axes[1].set_title("Stopping boundary", fontsize=9)
    fig.suptitle(f"Checking a {looks}-day test every day", fontweight="bold", fontsize=10)
    fig.tight_layout(); fig.savefig(CH / "05_peeking.png"); plt.close(fig)

    # ---------------- save ----------------
    (OUT / "decision_memo_raw_data.md").write_text(render_markdown(raw))
    (OUT / "decision_memo.md").write_text(render_markdown(res))
    (OUT / "analysis.json").write_text(json.dumps(res, indent=2, default=float))
    (OUT / "validation.json").write_text(json.dumps({k: v for k, v in val.items() if not k.startswith("_")},
                                                    indent=2, default=float))
    print("raw decision   :", raw["decision"])
    print("after exclusion:", res["decision"])
    print(json.dumps({k: v for k, v in val.items() if not k.startswith("_")}, indent=1, default=float))


if __name__ == "__main__":
    main()
