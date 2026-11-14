# Launch recommendation: Annual plan as the default on the pricing page

**Experiment:** Padho pricing page, 28 days, 514,919 visitors, 50/50 user-level split (simulated data).
**Engine verdict:** SHIP WITH CONDITIONS. **My recommendation:** roll out to **Tier-1 and Tier-2 cities only**, keep Monthly as the default in Tier-3, and confirm with a short follow-up test.

---

## 1. First, the data was broken, and the engine caught it
- The raw split was 49.67% treatment. The χ² test gave p = 2.1 × 10⁻⁶, a sample ratio mismatch, so the engine **refused to report any metric**.
- **Drill-down:** on days 4 and 5, treatment fell to about 42%, and only on Android (`01_srm_by_day.png`). The cause was Android build 7.4.1, which failed to send the treatment exposure event.
- **Fix:** exclude Android visitors assigned on days 4-5 **from both arms** (excluding from one arm would bias the result). After exclusion the split is 50.17% (p = 0.017, above the 0.001 SRM threshold), leaving 499,594 visitors.
- **Why it matters:** the users who went missing weren't random. Reading results without this check would have compared treatment-minus-some-Android-users against full control.

## 2. Results

| Metric | Control | Treatment | Relative change (95% CI) | Read |
|---|---|---|---|---|
| **Primary:** projected 12-month revenue / visitor | ₹68.02 | ₹72.50 | **+6.6% (+3.9% to +9.3%)** | ✅ clear win |
| Annual share of payers | 29.4% | 51.8% | +75.9% | the mechanism |
| First-payment revenue / visitor | ₹35.36 | ₹50.78 | +43.6% | cash comes in up-front |
| Paid conversion | 4.42% | 4.31% | **−2.7% (−5.2% to −0.1%)** | ⚠️ guardrail at risk |
| 7-day refund rate (of payers) | 3.80% | 4.30% | +0.50 pp (−0.02 to +1.03 pp) | ⚠️ guardrail at risk |
| Checkout error rate | 2.01% | 2.06% | +0.05 pp | ✅ pass |
| Learning sessions / visitor | 2.86 | 2.86 | +0.1% (CUPED: 49% variance removed) | no effect, as expected |

**Why "projected 12-month revenue" and not first payment?** An annual plan collects ₹1,999 up front, while a monthly subscriber pays ₹299 about 4.5 times. Counting only the first payment would overstate the win (+43.6% vs a true +6.6%). Choosing the right primary metric *before* the test is half the analysis.

**Guardrails** use non-inferiority: the *worst plausible* value has to stay inside the margin (conversion no worse than −5% relative, refunds no worse than +1.0 pp).
- **Conversion:** the CI lower bound is −5.2%, just past the margin.
- **Refunds:** the CI upper bound is +1.03 pp, just past the margin.
- Neither is proven harmful, but neither can be ruled out. That's why the verdict is conditional.

## 3. Where the conditions come from: Tier-3 cities

| City tier | 12-month revenue / visitor | Paid conversion |
|---|---|---|
| Tier 1 | **+8.0%** ✱ | −2.7% |
| Tier 2 | **+14.3%** ✱ | +3.5% |
| Tier 3 | **−11.2%** ✱ | **−13.9%** ✱ |

✱ significant after Benjamini-Hochberg correction across all 16 segment tests.

In Tier-3, the ₹1,999 sticker price scares users off: conversion falls by 14%, and the extra annual plans don't make up for it.

**Sizing the options (per 100K pricing-page visitors, projected 12-month revenue):**
- **Full rollout:** +₹4.48 per visitor, **about +₹4.5 lakh**.
- **Tier-1 and Tier-2 only** (Tier-3 stays on control): about +₹5.87 per visitor, **about +₹5.9 lakh (+8.6%)**.

Targeting earns about **31% more** than a full rollout *and* protects Tier-3 conversion.

## 4. Conditions for launch
1. **Confirm the segment finding.** Segment results are post-hoc. Run a 2-week confirmation test in Tier-1 and Tier-2 only, with conversion and refunds as pre-registered guardrails.
2. **Monitor refunds weekly** for 8 weeks after launch, since annual buyers refund more often. Roll back if the refund rate rises by more than 1 pp.
3. **Tier-3 follow-up:** test a cheaper annual plan or a quarterly plan instead of the ₹1,999 default.
4. **Fix release QA:** add an SRM alert on daily exposure counts so a broken build is caught on day 1, not after the test.

## 5. Why these numbers can be trusted (`outputs/validation.json`)

| Check | Result |
|---|---|
| 1,000 A/A tests, conversion | 3.7% false positives (target 5%) |
| 1,000 A/A tests, revenue | 4.2% false positives |
| Ratio metric, naive page-view-level test | **12.9% false positives**, about 2.6× too many |
| Ratio metric, delta method | 4.7% false positives ✅ |
| Peeking every day for 28 days, naive | **27.2% false positives** |
| Peeking with O'Brien-Fleming boundary | 4.6% ✅ |
| CUPED on learning sessions | 49% variance removed, so about half the sample size for the same power (29,867 vs 59,081 per arm for a 2% MDE) |
| CUPED on revenue | only 0.6%: 70% of visitors are new, with no pre-period history. CUPED is only as good as its covariate. |
