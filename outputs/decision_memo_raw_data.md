# Decision memo: Padho pricing page: Annual plan as default (Oct 2026)

## Decision: **INVALID - sample ratio mismatch; fix assignment/logging before reading results**

## 1. Data-quality gate (sample ratio mismatch)
- Raw split: control 259,162 vs treatment 255,757 (treatment share 49.67%); χ² p = 2.08e-06 → **SRM DETECTED** (threshold p < 0.001)

| dimension | value | control | treatment | treatment share | p |
|---|---|---|---|---|---|
| assign_day | 4 | 9,256 | 6,676 | 41.90% | 7.3e-93 |
| assign_day | 5 | 9,363 | 6,796 | 42.06% | 1.1e-90 |
| platform | android | 142,187 | 138,052 | 49.26% | 5.7e-15 |
| assign_day | 11 | 9,222 | 9,573 | 50.93% | 1.0e-02 |
| assign_day | 8 | 9,026 | 9,301 | 50.75% | 4.2e-02 |

## 2. Primary metric
| metric | control | treatment | diff | rel. lift | 95% CI (diff) | p | method |
|---|---|---|---|---|---|---|---|
| projected_12m_revenue_per_visitor | ₹68.25 | ₹72.36 | +4.11 | +6.0% | [+2.277, +5.934] | <0.0001 | Welch t-test + CUPED |

CUPED (pre-period sessions) removed 0.7% of variance (raw p = <0.0001).
Bootstrap 95% CI on the raw difference: [+2.31, +5.93].

## 3. Secondary metrics
| metric | control | treatment | diff | rel. lift | 95% CI (diff) | p | method |
|---|---|---|---|---|---|---|---|
| paid_conversion | 4.44% | 4.30% | -0.14 pp | -3.2% | [-0.25 pp, -0.03 pp] | 0.0135 | two-proportion z-test |
| annual_share_of_payers | 29.43% | 51.78% | +22.35 pp | +75.9% | [+21.10 pp, +23.60 pp] | <0.0001 | delta method (ratio) |
| first_payment_revenue_per_visitor | ₹35.47 | ₹50.68 | +15.20 | +42.9% | [+13.746, +16.659] | <0.0001 | Welch t-test |
| checkout_starts_per_pricing_view | 0.1524 | 0.1479 | -0.0044 | -2.9% | [-0.006, -0.003] | <0.0001 | delta method (ratio) |
| learning_sessions_per_visitor | 2.8619 | 2.8645 | 0.0019 | +0.1% | [-0.012, +0.016] | 0.7804 | Welch t-test + CUPED |

## 4. Guardrails (non-inferiority: the worst plausible value must stay inside the margin)
| guardrail | rule | status |
|---|---|---|
| paid_conversion | decrease ≥ -5% rel (CI lower -5.7% rel) | **AT RISK** |
| refund_rate_7d | increase ≤ +0.0100 (CI upper +0.0097) | **PASS** |
| checkout_error_rate | increase ≤ +0.0050 (CI upper +0.0017) | **PASS** |

## 5. Segments (Benjamini-Hochberg FDR 5% across all segment tests)
| dimension | segment | metric | rel. lift | p | p (BH) | significant |
|---|---|---|---|---|---|---|
| city_tier | 1 | projected_12m_revenue_per_visitor | +7.7% | 0.0001 | 0.0005 | ✅ |
| city_tier | 1 | paid_conversion | -3.0% | 0.1096 | 0.1462 |  |
| city_tier | 2 | projected_12m_revenue_per_visitor | +13.3% | 0.0000 | 0.0000 | ✅ |
| city_tier | 2 | paid_conversion | +2.6% | 0.2479 | 0.3051 |  |
| city_tier | 3 | projected_12m_revenue_per_visitor | -11.7% | 0.0001 | 0.0005 | ✅ |
| city_tier | 3 | paid_conversion | -14.4% | 0.0000 | 0.0000 | ✅ |
| platform | android | projected_12m_revenue_per_visitor | +5.2% | 0.0049 | 0.0130 | ✅ |
| platform | android | paid_conversion | -3.9% | 0.0268 | 0.0429 | ✅ |
| platform | ios | projected_12m_revenue_per_visitor | +7.4% | 0.0342 | 0.0497 | ✅ |
| platform | ios | paid_conversion | -2.5% | 0.4429 | 0.4724 |  |
| platform | web | projected_12m_revenue_per_visitor | +6.7% | 0.0074 | 0.0132 | ✅ |
| platform | web | paid_conversion | -2.3% | 0.3177 | 0.3631 |  |
| visitor_type | new | projected_12m_revenue_per_visitor | +4.9% | 0.0061 | 0.0132 | ✅ |
| visitor_type | new | paid_conversion | -4.4% | 0.0074 | 0.0132 | ✅ |
| visitor_type | returning | projected_12m_revenue_per_visitor | +7.7% | 0.0004 | 0.0011 | ✅ |
| visitor_type | returning | paid_conversion | -1.3% | 0.5114 | 0.5114 |  |

_Segment results are exploratory. A segment-specific launch should be confirmed with a follow-up test._
