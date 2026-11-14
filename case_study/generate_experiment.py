"""
Simulated A/B test for "Padho", a fictional exam-prep subscription app.

Test: PRICING PAGE. Control shows Monthly (₹299) first. Treatment pre-selects Annual (₹1,999,
"save 44%") as the default plan.

Ground truth planted in the data (the engine has to recover it):
  * treatment shifts plan mix towards Annual -> higher projected 12-month revenue per visitor
  * treatment slightly lowers paid conversion overall, and clearly in tier-3 cities (price shock)
  * no true effect on learning sessions (lets CUPED show a tighter CI around zero)
  * a LOGGING BUG: on days 4-5, ~50% of treatment users on the Android app were never logged
    -> sample ratio mismatch that must be caught before any metric is read

Output: case_study/data/pricing_test.csv.gz (one row per visitor)
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "data"
MONTHLY, ANNUAL = 299, 1999
MONTHLY_EXPECTED_PAID_MONTHS = 4.5          # historical average paid months for a monthly subscriber
VALUE_MONTHLY_12M = MONTHLY * MONTHLY_EXPECTED_PAID_MONTHS   # ₹1,345.5 projected 12-month value


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def simulate(n=520_000, seed=2026, days=28, srm_bug=True):
    rng = np.random.default_rng(seed)
    variant = np.where(rng.random(n) < 0.5, "treatment", "control")
    trt = variant == "treatment"
    assign_day = rng.integers(1, days + 1, n)
    platform = rng.choice(["android", "web", "ios"], n, p=[0.55, 0.30, 0.15])
    tier = rng.choice([1, 2, 3], n, p=[0.40, 0.35, 0.25])
    returning = rng.random(n) < 0.30

    engagement = rng.lognormal(0, 0.8, n)
    pre_sessions = rng.poisson(np.where(returning, 3.0, 0.4) * engagement)       # 28 days before assignment
    sessions = rng.poisson(np.where(returning, 3.2, 1.6) * engagement)            # during the test (no true effect)
    pricing_views = 1 + rng.poisson(1.2 * engagement ** 1.5)       # heavy users revisit pricing many times

    # ---- conversion ----
    logit = (-3.35 + 0.55 * np.log(engagement) + 0.5 * returning
             + np.select([tier == 1, tier == 3], [0.2, -0.3], 0.0))
    logit += trt * np.where(tier == 3, -0.16, -0.01)          # annual-default scares price-sensitive users
    converted = rng.random(n) < sigmoid(logit)

    # ---- plan choice ----
    p_annual = np.where(trt, np.where(tier == 3, 0.36, 0.55), 0.30)
    annual = converted & (rng.random(n) < p_annual)
    monthly = converted & ~annual
    revenue_first_payment = np.where(annual, ANNUAL, np.where(monthly, MONTHLY, 0))
    revenue_12m = np.where(annual, ANNUAL, np.where(monthly, VALUE_MONTHLY_12M, 0.0))

    # ---- checkout funnel (ratio metric: checkout starts per pricing-page view) ----
    # each visitor has their own propensity to click "checkout" -> views of one user are correlated
    p_cs = np.clip(rng.beta(1.1, 8.0, n) + 0.02 * np.log1p(engagement) - 0.004 * trt, 0.005, 0.95)
    checkout_starts = np.maximum(rng.binomial(pricing_views, p_cs), converted.astype(int))
    checkout_errors = rng.binomial(checkout_starts, 0.02)

    # ---- refunds within 7 days (annual buyers refund a bit more often) ----
    refunded = converted & (rng.random(n) < np.where(annual, 0.055, 0.035))

    df = pd.DataFrame({
        "user_id": np.arange(1, n + 1), "variant": variant, "assign_day": assign_day,
        "platform": platform, "city_tier": tier, "visitor_type": np.where(returning, "returning", "new"),
        "pre_sessions": pre_sessions, "sessions": sessions, "pricing_views": pricing_views,
        "checkout_starts": checkout_starts, "checkout_errors": checkout_errors,
        "converted": converted.astype(int), "annual_plan": annual.astype(int),
        "revenue_first_payment": revenue_first_payment, "revenue_12m": revenue_12m.round(1),
        "refunded": refunded.astype(int),
    })

    if srm_bug:   # Android app build 7.4.1 failed to send the exposure event for some treatment users
        bug = trt & (platform == "android") & np.isin(assign_day, [4, 5]) & (rng.random(n) < 0.50)
        df = df[~bug].reset_index(drop=True)
    return df


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    d = simulate()
    d.to_csv(OUT / "pricing_test.csv.gz", index=False)
    print(f"{len(d):,} visitors written -> {OUT / 'pricing_test.csv.gz'}")
    print(d.groupby("variant")[["converted", "annual_plan", "revenue_12m", "refunded"]].mean().round(4))
