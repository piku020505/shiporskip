# Decision memo: Padho pricing page: Annual plan as default (Oct 2026)

## Decision: **SHIP WITH CONDITIONS - primary improved; a guardrail cannot yet rule out harm**

## 1. Data-quality gate (sample ratio mismatch)
- Raw split: control 259,162 vs treatment 255,757 (treatment share 49.67%); χ² p = 2.08e-06 → **SRM DETECTED** (threshold p < 0.001)

| dimension | value | control | treatment | treatment share | p |
|---|---|---|---|---|---|
| assign_day | 4 | 9,256 | 6,676 | 41.90% | 7.3e-93 |
| assign_day | 5 | 9,363 | 6,796 | 42.06% | 1.1e-90 |
| platform | android | 142,187 | 138,052 | 49.26% | 5.7e-15 |
| assign_day | 11 | 9,222 | 9,573 | 50.93% | 1.0e-02 |
| assign_day | 8 | 9,026 | 9,301 | 50.75% | 4.2e-02 |

- Exclusion applied: Exclude Android app visitors assigned on days 4-5 (build 7.4.1 dropped treatment exposure events) from BOTH arms.
- After exclusion: treatment share 50.17%, p = 0.017 → **clean**. Analysed 499,594 of 514,919 visitors.

## 2. Primary metric
| metric | control | treatment | diff | rel. lift | 95% CI (diff) | p | method |
|---|---|---|---|---|---|---|---|
| projected_12m_revenue_per_visitor | ₹68.02 | ₹72.50 | +4.48 | +6.6% | [+2.625, +6.335] | <0.0001 | Welch t-test + CUPED |

CUPED (pre-period sessions) removed 0.7% of variance (raw p = <0.0001).
Bootstrap 95% CI on the raw difference: [+2.64, +6.38].

## 3. Secondary metrics
| metric | control | treatment | diff | rel. lift | 95% CI (diff) | p | method |
|---|---|---|---|---|---|---|---|
| paid_conversion | 4.42% | 4.31% | -0.12 pp | -2.7% | [-0.23 pp, -0.00 pp] | 0.0419 | two-proportion z-test |
| annual_share_of_payers | 29.44% | 51.79% | +22.35 pp | +75.9% | [+21.08 pp, +23.62 pp] | <0.0001 | delta method (ratio) |
| first_payment_revenue_per_visitor | ₹35.36 | ₹50.78 | +15.42 | +43.6% | [+13.941, +16.894] | <0.0001 | Welch t-test |
| checkout_starts_per_pricing_view | 0.1522 | 0.1479 | -0.0043 | -2.8% | [-0.006, -0.003] | <0.0001 | delta method (ratio) |
| learning_sessions_per_visitor | 2.8627 | 2.8649 | 0.0023 | +0.1% | [-0.012, +0.016] | 0.7487 | Welch t-test + CUPED |

## 4. Guardrails (non-inferiority: the worst plausible value must stay inside the margin)
| guardrail | rule | status |
|---|---|---|
| paid_conversion | decrease ≥ -5% rel (CI lower -5.2% rel) | **AT RISK** |
| refund_rate_7d | increase ≤ +0.0100 (CI upper +0.0103) | **AT RISK** |
| checkout_error_rate | increase ≤ +0.0050 (CI upper +0.0016) | **PASS** |

## 5. Segments (Benjamini-Hochberg FDR 5% across all segment tests)
| dimension | segment | metric | rel. lift | p | p (BH) | significant |
|---|---|---|---|---|---|---|
| city_tier | 1 | projected_12m_revenue_per_visitor | +8.0% | 0.0001 | 0.0003 | ✅ |
| city_tier | 1 | paid_conversion | -2.7% | 0.1516 | 0.1866 |  |
| city_tier | 2 | projected_12m_revenue_per_visitor | +14.3% | 0.0000 | 0.0000 | ✅ |
| city_tier | 2 | paid_conversion | +3.5% | 0.1247 | 0.1663 |  |
| city_tier | 3 | projected_12m_revenue_per_visitor | -11.2% | 0.0002 | 0.0008 | ✅ |
| city_tier | 3 | paid_conversion | -13.9% | 0.0000 | 0.0000 | ✅ |
| platform | android | projected_12m_revenue_per_visitor | +6.3% | 0.0011 | 0.0029 | ✅ |
| platform | android | paid_conversion | -2.9% | 0.1074 | 0.1562 |  |
| platform | ios | projected_12m_revenue_per_visitor | +7.4% | 0.0342 | 0.0547 |  |
| platform | ios | paid_conversion | -2.5% | 0.4429 | 0.4724 |  |
| platform | web | projected_12m_revenue_per_visitor | +6.7% | 0.0074 | 0.0148 | ✅ |
| platform | web | paid_conversion | -2.3% | 0.3177 | 0.3631 |  |
| visitor_type | new | projected_12m_revenue_per_visitor | +5.2% | 0.0041 | 0.0094 | ✅ |
| visitor_type | new | paid_conversion | -4.1% | 0.0144 | 0.0257 | ✅ |
| visitor_type | returning | projected_12m_revenue_per_visitor | +8.7% | 0.0001 | 0.0003 | ✅ |
| visitor_type | returning | paid_conversion | -0.5% | 0.8165 | 0.8165 |  |

_Segment results are exploratory. A segment-specific launch should be confirmed with a follow-up test._
