# Altitude and elite race performance: the technical audit

[Project overview](README.md) · [Reproduce the analysis](REPRODUCING.md)

The investigation began with a physics-inspired model and apparent group differences. It ended with a narrower finding: altitude terms provided a small predictive improvement, while the physiological interpretation remained unresolved. An apparent reversal in group differences also disappeared when the evaluation code was corrected.

This report follows the checks behind that conclusion. Section 3 gives the chronological prediction results and code corrections; sections 4–5 inspect the comparison groups; section 6 sets out the remaining limitations.

Numbers labeled “corrected audit” come from [results/audit.json](results/audit.json). Historical results are labeled separately. The [saved fresh-download report](results/fresh_download.json) records an exact reproduction of the audited result sections using the existing auxiliary inputs and environment.

## 1. The question and the model

The initial question was whether a pooled regression could describe the transition from altitude-associated sprint gains to distance-race penalties, then explain differences across athletes and groups.

The working model uses:

```text
log(race_time) ≈ controls
              + α_drag × altitude × velocity² / area_proxy
              + α_aerobic × altitude × log(prior_best)
              + corresponding interactions with is_women
```

Altitude is in metres. `prior_best` is the best qualifying sea-level time in the preceding 545 days, excluding race day; velocity is event distance divided by that time. The area proxy scales with mass to the two-thirds power. Mass comes from retrospective athlete records when available, otherwise country/event/sex lookups.

These are **physics-inspired basis functions**, not direct measurements of drag work, aerobic capacity, or oxygen debt. In particular, placing the area proxy in a denominator is a modeling choice whose physical derivation needs further validation. Matching expected signs does not validate the whole parameterization.

Controls in the corrected base model are log prior-best time, year, day of year, wind, and event-by-sex indicators. The expanded specification adds velocity, mass, area, and nonlinear race-history terms. Both include personal-best time. The interaction ratio `γ = δ / α` describes the fitted difference relative to the men's coefficient; it can become unstable when the denominator is small.

## 2. What changed after each check

| Question | Check | Current interpretation |
|---|---|---|
| Does a plausible pooled fit establish physiology? | Compare signs and historical fitted magnitudes | Plausibility motivates further tests; it does not identify a mechanism |
| Is race history available before prediction? | Replace career-wide features with past-only windows | Race-result leakage is addressed in the supported audit; static mass proxies remain retrospective |
| Does altitude help predict future races? | Expanding date blocks with an explicit PB-adjusted baseline | Small positive aggregate improvement, with a negative earliest fold |
| Can the groups be compared at the same performance level? | Inspect within-event prior-best ranges | No overlap in any of eight events; comparisons depend on extrapolation assumptions |
| Does residual analysis reverse the group difference? | Correct preprocessing and residualize both sides | The earlier sign reversal does not reproduce and is withdrawn |
| Does comparing each athlete with themselves solve selection? | Inspect qualifying careers by group and nationality proxy | Distance-event comparison groups remain small and imbalanced |
| What else changes when an athlete races at altitude? | Count home/away venue countries within qualifying 5000m careers | Altitude and race context are strongly associated; the slope cannot isolate physiology |

These checks address different failure modes. Passing one does not compensate for failing another.

## 3. Corrected temporal evaluation

The analysis sample contains **93,990 race rows from 1965-11-30 through 2023-06-30**, spanning 100m to 10000m and both recorded sex categories. The archive source is [mexwell’s World Athletics Database on Kaggle](https://www.kaggle.com/datasets/mexwell/world-athletics-database), which credits thomascamminady. Kaggle displayed version 1, updated July 23, 2024, with MIT license metadata when checked on September 30, 2026. [DATA_PROVENANCE.json](DATA_PROVENANCE.json) records the attribution and local archive fingerprints. The sample inherits selection from the elite archive and the enriched dataset. The feature loader excludes indoor races, missing altitude, missing prior-best history, and sprint rows outside its conservative `|wind| ≤ 2` filter or with missing wind.

The corrected protocol splits unique race dates into six chronological blocks. The first block initializes training; each following block is tested using all earlier blocks. Same-day races stay together. Scaling and nuisance regression fit only on training rows, with ridge regularization fixed at 1 rather than chosen using future outcomes.

This is rolling prediction: previous results within a test period can inform a later race's prior-best feature, while fitted model parameters remain fixed for the block. It does not represent a single forecast made at the beginning of the entire test period.

For each fold, outcome and altitude basis columns are residualized against the same training controls. The physics coefficients are fitted on training residuals and evaluated on future races. The primary metric is:

```text
relative SSE improvement = 1 − SSE(full model) / SSE(control-only baseline)
```

Positive values mean lower squared error in log race time than the explicit baseline. This is not a percentage change in race time, a percentage-point change in overall R², or a causal effect size.

### Corrected audit: future-race prediction

| Test period | Test rows | Base controls: SSE improvement | Expanded controls: SSE improvement |
|---|---:|---:|---:|
| 1986-08-31–1996-08-19 | 11,061 | −0.90% | −0.78% |
| 1996-08-20–2003-06-12 | 15,679 | +1.23% | +1.09% |
| 2003-06-13–2010-06-12 | 19,803 | +0.43% | +0.35% |
| 2010-06-13–2017-05-06 | 20,807 | +0.65% | +0.59% |
| 2017-05-07–2023-06-30 | 21,803 | +1.15% | +1.13% |
| **Pooled held-out rows** | **89,153** | **+0.63%** | **+0.59%** |

Base-model log-time RMSE changes from **0.010533 to 0.010500**. Expanded-model RMSE changes from **0.010578 to 0.010547**. The improvement is small; expanded controls do not outperform the base specification on this aggregate metric. No confidence interval for the difference is supplied, so these numbers are descriptive evidence of prediction performance, not a significance claim.

The training-fold interaction ratios are unstable: base drag γ ranges from about 15% to 59%, and aerobic γ from 20% to 542%. Era composition, model misspecification, weak denominators, and changing race contexts can all contribute. The ratios do not by themselves quantify a stable biological difference.

### Corrections to the original evaluation

The previous temporal script omitted `log_pb` from its baseline while describing a comparison with the PB-adjusted original model. It also reported residual R² against a centered residual denominator, which was not the direct improvement over the control-only predictor. The corrected audit includes `log_pb`, uses date boundaries, fixes regularization, and reports baseline-relative error. Consequently, the old and new fold tables are different protocols, not a one-variable ablation.

The previous residual script transformed controls using altitude regression slopes estimated on the full dataset before splitting. That let future covariates influence preprocessing. It also residualized controls against altitude rather than residualizing outcome and exposure against controls; it was not a standard FWL adjustment.

The replacement residualizes **both outcome and altitude basis columns against the same controls**, using training-only nuisance fits. With ridge, this is regularized partialling-out rather than the exact OLS FWL identity. A second-stage fit across out-of-fold residuals estimates descriptive coefficients; those rows are not a fresh test of that second-stage fit.

The corrected pooled out-of-fold ratios are approximately **+31% drag / +31% aerobic** for base controls and **+25% / +28%** for expanded controls. The historical −67% / −29% sign-reversal claim is therefore withdrawn. Neither the old reversal nor the corrected agreement establishes causality.

## 4. Performance support

### Corrected audit: prior-best ranges

| Event | Slowest men's prior best, s | Fastest women's prior best, s | Rows in shared range |
|---|---:|---:|---:|
| 100m | 10.30 | 10.54 | 0 |
| 200m | 20.70 | 21.45 | 0 |
| 400m | 45.50 | 47.99 | 0 |
| 800m | 106.00 | 114.25 | 0 |
| 1500m | 218.00 | 230.07 | 0 |
| 3000m | 464.97 | 492.19 | 0 |
| 5000m | 810.00 | 846.62 | 0 |
| 10000m | 1690.00 | 1741.03 | 0 |

These are the actual rolling prior-best features in the model sample, not all-time race records. They differ from some values quoted in the original narrative.

There is no observed support for comparing groups at the same absolute prior-best time within an event. A parametric model can still estimate coefficients, but attributing group differences separately from performance requires assumptions about how the response extends across the gap. This is a **lack-of-overlap problem**, not proof that the design matrix has exact linear collinearity.

The earlier within-sex tier and flexible-composition experiments remain useful exploratory prompts: examine heterogeneity and whether proxies encode group membership. Their nominal significance and in-sample proxy predictability do not validate a physiological explanation. Those experiments are not rerun by the supported audit.

## 5. Within-athlete comparisons and their remaining limits

The descriptive career probe fits `log(time) ~ intercept + altitude + centered_year` separately for each athlete/event career. Eligibility requires at least eight races, at least two above 500m, sufficient altitude variation, and a successful fit. The corrected audit reproduces **1,343 qualifying careers**.

An athlete intercept handles time-invariant baseline differences. It does not hold fitness, training base, weather, competitive context, or altitude adaptation fixed over a career, and it does not make the athletes contributing slopes representative of other athletes.

### Corrected audit: distance-event composition

The existing script uses a hand-selected nationality set as a proxy for possible altitude exposure. It includes East African countries, selected transfer destinations, and high-altitude American countries. It is not a measurement of residence, training elevation, birthplace, or adaptation.

| Event | Men: careers | Men: proxy-positive | Women: careers | Women: proxy-positive |
|---|---:|---:|---:|---:|
| 800m | 75 | 40 (53%) | 70 | 17 (24%) |
| 1500m | 61 | 43 (70%) | 41 | 19 (46%) |
| 5000m | 29 | 28 (97%) | 20 | 13 (65%) |
| 10000m | 16 | 16 (100%) | 5 | 5 (100%) |

At 5000m, excluding this proxy-positive group leaves **one man and seven women**. At 10000m it leaves nobody. This limits the comparison; it does not demonstrate that “100% of the effect” is caused by nationality or that the effect disappears outside the group.

The descriptive precision-weighted 5000m slopes remain approximately 9.93×10⁻⁶ per metre for men and 1.80×10⁻⁵ for women. Their ratio is about 1.81. The report retains weighted and median slopes but omits confirmatory t-statistics: the legacy weights use ordinary within-career regression errors and do not resolve between-athlete heterogeneity or shared-meet dependence.

### Corrected audit: venue context

Among outdoor 5000m races for qualifying proxy-positive careers, “home” means venue country equals the athlete country recorded on that race row. Unknown countries are counted separately.

| Altitude band | Home | Away | Unknown |
|---|---:|---:|---:|
| Below 200m | 0 | 692 | 0 |
| 200–500m | 0 | 118 | 0 |
| Above 500m | 129 | 19 | 0 |

About **87% of races above 500m are home races**, while every observed race below 200m in this defined sample is away. This replaces the old home/away percentages with explicit, reproducible denominators.

Race context therefore remains a credible alternative explanation for some of the slope. The table does not measure pacing, field strength, tactical racing, or travel effects, so it cannot show which mechanism causes the difference. It also shows some away races at altitude: altitude and home status are strongly associated, not mathematically identical.

Historical sprint comparisons did not reject equality under their original standard-error assumptions. That is not an equivalence test or a “solid null,” and it does not prove that a tier artifact explains the pooled interaction.

## 6. What the data support

The corrected analysis supports a small incremental predictive contribution from these altitude basis functions: about 0.6% less held-out squared error than the control-only baseline under this evaluation protocol. This does not establish that altitude’s physiological effect is small. It documents unstable interaction ratios and limited performance/context support for group comparisons. The nationality and venue audits explain why within-athlete adjustment alone is insufficient to establish the proposed interpretation.

It does **not** identify sex-specific physiology, establish equality of sprint responses, prove a home/away causal mechanism, or establish that the aggregate altitude coefficients are causally identified. A larger sample can reduce random error without removing selection or confounding. Agreement with a physics narrative is a plausibility check, not protection from those problems.

Further limitations remain:

- **Sampling and measurement:** elite-list thresholds, missing venues/weather, name-based athlete keys, and retrospective mass records can affect results. Nationality-based mass and exposure proxies embed group assumptions.
- **Validation target:** the same athletes and venues can appear in training and test periods. Athlete-held-out and venue-held-out evaluation would answer different questions.
- **Uncertainty:** repeated athletes, shared meets, nuisance estimation, and many exploratory specifications are not covered by the original OLS t-statistics. Cluster-aware inference and sensitivity analysis remain unfinished.
- **Protocol selection:** the corrected analysis was designed after inspecting the dataset and earlier outcomes. Its future-date folds are useful diagnostics, not a prospectively untouched final test.
- **Data provenance:** all 16 archive files match a fresh version-1 download, and an isolated rebuild reproduces every outdoor derived record and audited result. The rebuild reuses the existing venue table and mass proxies; their measurement accuracy and the installation of a fresh software environment were not independently validated.

Better performance overlap and measured race context would reduce extrapolation. A controlled within-person design could address different confounding problems. Neither more rows nor another regression adjustment automatically resolves identification.

## 7. The transferable ML lesson

The contribution is the audit trail: define what a feature knows at prediction time, measure improvement against the right baseline, inspect who supplies the relevant variation, and narrow the claim when the comparison is unsupported. Audit code deserves the same scrutiny as model code.

The strongest change in this revision is a correction to the critique itself. Once the residual analysis was repaired, its dramatic sign reversal vanished. Keeping that correction visible makes the case study more useful than a narrative in which every successive test conveniently confirms the final story.
