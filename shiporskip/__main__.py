"""Command line:  python -m shiporskip --data <csv> --config <json> [--exclude "<pandas query>"] [--out <dir>]

Example:
  python -m shiporskip --data case_study/data/pricing_test.csv.gz --config case_study/config.json \
      --exclude "platform == 'android' and assign_day in [4, 5]" --out outputs
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from .analyze import analyze
from .report import render_markdown


def main():
    ap = argparse.ArgumentParser(prog="shiporskip")
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--exclude", default=None, help="pandas query selecting rows to EXCLUDE (both arms)")
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()

    df = pd.read_csv(a.data)
    cfg = json.loads(Path(a.config).read_text())
    excl = (lambda d: d.eval(a.exclude)) if a.exclude else None
    res = analyze(df, cfg, exclude=excl)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(res, indent=2, default=float))
    (out / "decision_memo.md").write_text(render_markdown(res))
    print(res["decision"])
    print(f"wrote {out / 'decision_memo.md'} and {out / 'analysis.json'}")


if __name__ == "__main__":
    main()
