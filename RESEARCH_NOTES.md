# Historical research notebook — altitude and running performance

> **Superseded exploratory notes.** This file preserves the hypotheses and
> interpretations recorded during the original investigation. It is not the
> current conclusion or a reproduction report. See [WRITEUP.md](WRITEUP.md)
> for the corrected case study and [results/audit.json](results/audit.json)
> for the rerun. In particular, significance did not establish biology;
> nationality did not measure altitude residence; morphology adjustment did
> not isolate a causal remainder; and the original temporal/residual audits
> required correction. Historical coefficient tables below have not all
> been regenerated. The original equation's density scaling and units also
> require reconciliation before reuse.

## Question
How does altitude reduce / increase race time across the sprint→middle→distance spectrum, and can we decompose the net effect into drag savings and O₂ debt?

## Original pooled result (historical)

Pooled regression across 100m, 200m, 400m, 800m, 1500m, 3000m, 5000m, 10000m × men + women, calibrated on 93,990 athlete-agnostic results (1958–2023) from the World Athletics archive:

```
Δt / t  =  -6.15e-5 · v_avg² · Δρ  +  1.18e-3 · log(t_race) · Δρ
              ↑                       ↑
              drag savings (β=-6.15e-5, t=-24.4)
                                      O₂ debt (β=+1.18e-3, t=+25.3)
```

where `v_avg = distance / pb` (mean race velocity, m/s) and `t_race = pb` (seconds). Δρ in arbitrary scaling units; substitute `Δρ = -110 × altitude_m / 1000` for typical sea-level→altitude transitions.

Crossover where the two terms cancel: ~400m race time (45-50s).

## Predicted Mexico City (2240m) Δs by event (matches published estimates):

| Event | predicted Δs |
|---|---|
| 100m M | −0.075s |
| 200m M | −0.106s |
| 400m M | −0.038s |
| 800m M | +0.45s |
| 1500m M | +1.67s |
| 5000m M | +9.80s |
| 10000m M | +23.1s |

## Methodology arc — what we learned in order

1. **Naive altitude-only regression on top-500/yr scrape** (9k rows): noisy signals, men's 400m positive, women's 400m null. Athlete fixed-effects masked talent variation.

2. **Athlete-agnostic with sea-level rolling SB + world-rank tier**: cleaner identification. β ∝ d^1.08 — drag-time scaling.

3. **Added 60m indoor + 400m outdoor + season-of-year + championship-year features**: orthogonal controls, didn't move altitude estimate. Confirmed the effect is real, not selection.

4. **Added air density ρ via Meteostat weather lookup** (27,985 rows with ρ): showed cool weather at altitude meets confounded the altitude estimate. Spec C (alt | δT) revealed the *pure pressure* effect was different from the *bundled altitude* effect.

5. **Replaced WA scraper with a 191k-row Kaggle archive dump** (1958–2023): increased nominal t-statistics from ~3 to ~24; repeated races and confounding limit their interpretation.

6. **Specialization split for 400m using race counts** (n_200m, n_400m, n_800m): showed athlete profile heterogeneity but the all-time-list filter pre-filters most variation out. Residual signal weak.

7. **Endurance-demand reframing** (pb at distance as continuous proxy): resolved that men's 400m altitude effect is uniform across pb, women's 400m has signal direction consistent with O₂-bound athletes hurt more (but confounded with venue selection).

8. **Pooled across all distances and sexes via race-time-pb interaction**: one equation, one crossover (~71s pure altitude, ~162s without weather control). Unified men/women under same physics.

9. **Tested 4 functional forms** (linear, drag-physics with d², saturating). Linear specs over-predict drag savings at sprints because they don't enforce the physical bound (drag share of energy ≈ 1.5–3% for sprints).

10. **Final spec — log(y) with v²·alt and log(pb)·alt**: physics-correct two-component decomposition with realistic predictions across 100m–10000m. Drag scales with v² (capturing that drag work peaks at top speed and amplifies with velocity variability per Jensen). O₂ debt grows logarithmically with race time (saturating aerobic share).

## CP-based physiology test (frontier attempt, 2026-04-30)

Fit (CV, W') per athlete via critical-power model `d = CV·t + W'` from multi-distance PBs (sea-level legal, distances ≥800m). 2,069 athletes with stable fits. Re-ran the altitude regression replacing v_avg and pb with `(v_race/CV)²` and `W_spent/W'`.

**Result: sex interaction ratio unchanged from −0.26 to −0.24/−0.26.**

The 2-parameter CP model is too crude to absorb sex-specific biology. Closing the residual 25% would need direct measurements (VO₂max in mL/kg/min, hemoglobin mass, body composition, lactate threshold) that don't exist in race archives. See `compute_cp.py`, `model_physiological.py`.

## The realistic frontier: imputation via calibration dataset

Race-day physiological measurement isn't viable (the mask degrades the performance you're measuring). The realistic path:

1. **Compile published lab datasets** — sports science papers with VO₂max + race PBs on samples of 20-200 athletes. Foster, Joyner, Saltin, Mooses (Kenyan runners), Wilber (altitude training), etc. Probably 1,000-2,000 calibration athletes across all studies.
2. **Build imputation model** on calibration set: `VO₂max = f(race_PBs, sex, age)`. Modern ML on this is straightforward.
3. **Impute physiology for the 200k archive** using the imputation model.
4. **Re-run the altitude regression** with imputed VO₂max + (CV, W') from race PBs jointly. Test if sex × altitude residual now drops below 10%.

This is a 2-3 week project — finding/digitizing published lab datasets is the bottleneck. But it's the only realistic way to close the loop without intrusive at-race measurement.

## Sex differences: physics same, biology not

A model with `sex × alt × v²` and `sex × alt × log(pb)` interactions shows both terms significant at t≈±3.7 — magnitudes ~25% of main coefficients. Separate fits give:

| | β(alt × v²) | β(alt × log pb) |
|---|---|---|
| MEN (N=42,652) | −5.28e−8 | +1.01e−6 |
| WOMEN (N=51,338) | −7.44e−8 | +1.40e−6 |

Women's coefficients are larger in absolute value on both terms. Physical interpretation: drag and O₂ are universal, but the *biological substrate* (aerobic share at given race duration, power-to-CdA ratio, O₂ delivery capacity) differs between populations. The same physics equation, evaluated at different biological parameters.

The all-time-list filter creates **zero pb overlap** between sexes at any distance, so we can't test the cleanest version (does a sub-elite man with woman-equivalent v, pb match an elite woman?). NCAA data with overlapping performance distributions would resolve this — would expect coefficient gap to *narrow but not vanish* once selection is removed.

## What couldn't be answered with this data

1. **Tier × altitude interaction** (do top-tier sprinters benefit more from altitude in absolute seconds?) — top-10 athletes almost never race at altitude (championships at sea-level). Would need TFRRS-level NCAA data with mixed altitude/sea-level seasons.

2. **Phase-specific decomposition of altitude effect within a 100m/200m race** (acceleration vs peak velocity vs deceleration) — would need 10m splits. WA biomechanics reports cover ~10 championships but all sea-level.

3. **Velocity variability amplification of drag** — Jensen's inequality on `∫v³ dt` says velocity spikes amplify drag work. We approximate this with v_avg² but cannot directly measure ∫v³ without race splits.

4. **Synoptic pressure** (storm-system anomalies) — Meteostat's `pres` is MSLP-reduced; we back-converted to station pressure using a standard scale-height assumption. Real local pressure variations would tighten estimates by ~1-2% on the SE.

## Files

- `archive_data/` — 16 CSVs from the WA all-time top-list dump (1958–2023, 100m–10000m, men + women)
- `dataset_all.csv` — 191,378 raw rows (joined with venue altitudes via `venues.py`)
- `dataset_v3.csv` — 97,530 rows after enrichment (per-distance sea-level rolling SB + world rank + season features)
- `dataset_v4.csv` — 27,985 rows with full ρ from Meteostat (lat, lon, T, P, RH, derived ρ)
- `geocode_cache.json` / `meteostat_cache.json` / `station_cache.json` — fetched once, persistent

## Key scripts

- `scrape.py` — World Athletics toplist scraper (fallback before archive dump)
- `build_dataset_archive.py` — ingest archive CSVs + scraped 60m indoor → unified format
- `venues.py` — venue → altitude lookup (971 curated + Nominatim/Open-Meteo fallback)
- `enrich_v3.py` — per-distance pre-race rolling SB, world rank, tier, season features
- `weather_meteostat.py` — Meteostat-based weather + ρ lookup (replaces Open-Meteo which rate-limits)
- `model_pooled_velocity2.py` — final spec K (the published equation above)
- `model_pooled_specs.py` — alternative specs side-by-side comparison
- `model_400_specialization.py` / `model_endurance_demand.py` — heterogeneity probes (mixed results)

## L3: cohort-resolved coefficients (2026-04-30)

Reframed: the pooled spec is a remote-sensing instrument; race outcomes project latent physiology and (β_drag, β_O₂) are what the lens measures. L3 asks whether the lens has resolution along human axes — does refitting (K) per cohort produce coefficient differences that tell a coherent physiology story? Code: `model_cohort_cuts.py`. Three cuts:

### Cut 1 — PB-tier (ability axis), pooled across events

| tier | n | β_drag (×1000) | t | β_O₂ (×1000) | t |
|---|---|---|---|---|---|
| 1 (elite) | 27,982 | -0.0001 | -23.1 | **+0.0019** | +27.8 |
| 2 (mid) | 46,147 | -0.00005 | -11.8 | +0.0008 | +12.6 |
| 3 (low) | 19,861 | -0.00001 | -3.0 | -0.0002 | -1.6 |

Wald β_O₂ equality: χ²=260.7, dof=2, **p=2.4e-57**. Monotone, exactly the physiology direction: at elite level athletes operate near the O₂ ceiling so altitude bites hard; sub-elites are bottlenecked by training/fitness and altitude is not the binding constraint.

### Cut 2 — Geography (training-nation altitude), within event

Pooled cut is a confound: alt-nation cohort (KEN/ETH/ERI/UGA/MAR/etc.) is 99% distance, sea-nation is 80% sprints. Fixing the event removes the event-mix confound:

| event | group | n | β_O₂ (×1000) | t |
|---|---|---|---|---|
| 5000m | alt-nation | 3,613 | **+0.0027** | +3.4 |
| 5000m | sea-nation | 2,430 | **+0.0144** | +6.4 |

**Sea-level cohort shows 5.3× larger O₂ penalty at 5000m, p=3.6e-7.** This suggested an altitude-adaptation interpretation at the time; later support and context audits prevent that causal reading. 10000m points the same way (sea 0.0073 vs alt 0.0016) but underpowered (n~1k each, p=0.12). 1500m noisy (log(pb) variation too small within event for clean identification).

### Cut 3 — Specialization (≥80% one-distance), within tier

| group | n | β_O₂ (×1000) | t |
|---|---|---|---|
| specialist (elite) | 12,632 | +0.0012 | +8.5 |
| generalist (elite) | 15,330 | +0.0017 | +16.9 |

Generalists show ~40% larger O₂ penalty even within elite tier (χ²=7.93, p=0.005). Reading: generalists race events outside their primary strength, so they sit further from physiological optimum and altitude has more leverage on already-suboptimal performance.

### Verdict

The lens has clear, monotone, interpretable resolution along **ability** (cut 1) and **training-nation** (cut 2) axes. Cut 2 is an exploratory association; nationality, selection, and race context remain competing explanations. Cut 3 is suggestive and needs more controls.

This validates the L2 step (replace `log(pb)` with explicit latent variables — aerobic fraction, fatigue resistance — anchored to lab data via L4 imputation).

### Methodological caveat

Within-event PB-tier cuts (e.g. PB-tier within 100m) showed flipped/unstable signs because v² and log(pb) become quasi-collinear once event is fixed. The pooled cut works only because variation in event distribution provides identification of both physics channels simultaneously. Cohort cuts that hold event fixed should report β_O₂ only or interpret coefficients jointly.

## L2 step 1: morphology-controlled spec K′ (2026-04-30)

The 5000m geography result raised an obvious confound: KEN/ETH distance runners (53.4 kg mean) are ~10% smaller than European/American distance runners (59.5 kg mean), so they have a smaller frontal area and gain LESS from reduced ρ at altitude. That morphology effect could leak into β_drag and (via joint fit) β_O₂, producing a fake "altitude adaptation" signal.

### Spec change

- **K (original)**:  log(y) ~ alt × v²        + alt × log(pb)
- **K′ (morphology)**: log(y) ~ alt × v² / A  + alt × log(pb)

where A ∝ mass^(2/3) is the area proxy, with country-mean masses from published sport-science (`anthropometrics.py`: Mooses, Wilber, Beis, Joyner, Costill, Tanaka, Billat). 99.7% of 5000m rows resolve to non-imputed country values.

### Result — geography gap shrinks but survives

Wald χ² (unitless across spec change) for `H₀: β(alt-nation) = β(sea-nation)`:

| event | channel | K (orig) | K′ (morph) | reduction |
|---|---|---|---|---|
| 5000m | β_drag | 22.75 | 16.56 | **27%** |
| 5000m | β_O₂ | 25.88 | 17.97 | **31%** |
| 10000m | β_drag | 1.88 | 0.17 | 91% (uninformative — see below) |
| 10000m | β_O₂ | 2.40 | 0.31 | 87% (uninformative) |

At 5000m the geography gap remains highly significant under K′ (p=2.3e-5 for β_O₂), but ~30% of the apparent altitude-adaptation signal was explained by country-level body size. The residual association remained under this specification. A reduction in a Wald statistic is not a percentage of an effect explained, and the remaining association does not establish an adaptation mechanism.

**The 10000m χ² collapse is NOT evidence of morphological confound** — it's a statistical artifact of insufficient between-group variation in A. Mean-mass gap between alt- and sea-nation cohorts:

| event | alt-nation mass | sea-nation mass | gap | sea-nation top country |
|---|---|---|---|---|
| 5000m | 53.4 ± 4.5 kg | 59.5 ± 5.0 kg | 6.1 kg | USA (22%) |
| 10000m | 54.4 ± 3.5 kg | 57.1 ± 5.8 kg | 2.7 kg | **JPN (31%)** |

Elite 10000m self-selects for small builds across all nationalities: the sea-nation cohort is dominated by Japanese distance runners (58 kg, nearly identical to alt-nation 54.4 kg). Dividing by A in spec K′ mostly adds noise rather than absorbing systematic between-group variance, which mechanically deflates the χ². The 10000m is structurally uninformative for this morphology test — only 5000m has enough between-group A variation to identify a confound. **The 5000m number is the result.**

### Result — PB-tier monotone pattern is *not* a morphology artifact

| channel | K (orig) | K′ (morph) |
|---|---|---|
| β_drag (across tiers) | χ²=194.9 | χ²=**232.4** |
| β_O₂ (across tiers) | χ²=260.7 | χ²=**293.9** |

Adding morphology *strengthens* the tier-monotone pattern (chi² up). The ability gradient is independent of body size, as it should be — physiology (proximity to O₂ ceiling) varies within tier even at fixed body type.

### Verdict for the inversion frame

**Morphology absorbs altitude-attributed variance only where morphology varies between cohorts** — substantially at 5000m (Δmass = 6.1 kg), negligibly at 10000m (Δmass = 2.7 kg, sea-nation 31% Japanese). This pattern is exactly what physics predicts of a genuine area channel: A is doing real work where it has leverage and stays out of the way where it doesn't. If A had reduced the effect equally across events it would look like a generic variance soak; the event-dependence is itself evidence that the decomposition is structurally correct.

Three layers now behaving as theory requires:
1. **Physics** — drag responds to v²/A as Bernoulli demands.
2. **Morphology** — explains gap fraction in proportion to between-cohort A variance.
3. **Physiology** — what survives once morphology is accounted for.

Spec K′ (drag = `alt × v² / A`) is the correct physics — drag-per-unit-area is what the channel should encode — so it becomes the default for future analyses. The 5000m geography gap survives at p=2.3e-5 with ~30% morphological share; the PB-tier monotone pattern is fully independent of morphology (χ² actually rose under K′). 10000m provides limited identification due to convergent morphology across cohorts; inference relies on 5000m where between-group variation is sufficient.

Code: `model_morphology_test.py`. Country anthropometric table: `anthropometrics.py`.

### What this unlocks for L2 proper

Country-mean A is a coarse proxy. The cleanest next step is the user's **L2 latent expansion**: replace `log(pb)` with an estimated aerobic-fraction latent that is fit jointly with athlete-level CdA derived from competition v_avg residuals. NCAA data (TFRRS scrape, parked) gives within-country body-type variation needed for athlete-level A, but country-level A already gets us 80% of the diagnostic value at zero data cost.

## L2 ceiling test — race-data-only refinements (2026-04-30, `model_k_double_prime.py`)

Tried two L2 refinements on existing data:

1. **A_dominant**: replace race-event A lookup with athlete's dominant-event A (a 100m specialist racing 400m gets 100m-sprinter morphology, not 400m-sprinter morphology).
2. **Φ = (v_pb/CV)²**: replace `log(pb)` in the O₂ channel with proximity-to-critical-velocity, using CP fits from `cv_w_per_athlete.json` (2069 athletes).

Both fail to add resolution beyond K′:

| spec | 5000m β_O₂ χ² | tier β_O₂ χ² |
|---|---|---|
| K (raw) | 25.88 | 260.75 |
| K′ race-event A | 17.97 | 293.91 |
| K′ dominant-event A | 18.79 | 294.64 |

**Reasons for ceiling**:

- **A_dom ≈ A_race**: ~85% of athlete-rows are event-specialists (≥80% single-distance), so dominant-event lookup yields nearly identical A. The within-event morphology variation that NCAA data would provide doesn't exist in country-mean coordinates.
- **CV-based Φ is collinear with the drag channel**: Φ = (v/CV)² and drag = v²/A both scale as v² with athlete-specific denominators. The joint fit cannot identify them separately — initial run produced sign-flipped β_drag and chi² collapse from collinearity, not real signal absorption. (First version had a separate endogeneity bug — Φ used race-time velocity v_race=dist/t while LHS is log(t), creating mechanical 1/t² ↔ log(t) inverse dependence. Fixed by using v_pb=dist/pb. Even after fix, collinearity remained.)
- **log(pb) is functionally distinct from v² by construction**: log(pb) ∝ −log(v) + log(dist), which is why the original K spec separates channels cleanly. (v/CV)² loses this orthogonality.

**Conclusion**: K′ is the production spec. The race-data-only lens has saturated — log(pb) already absorbs the per-event aerobic-share signal, country-mean A already absorbs the cohort-level morphology signal, and no race-derived athlete feature adds independent identification. Going further requires genuinely new data: NCAA-level athlete body composition (within-country A variation), or lab-anchored physiology (VO₂max, Hb mass) to upgrade `log(pb)` from a cross-event proxy to interpretable units.

## Next steps if revisited

1. **Scrape TFRRS NCAA D1+D2 lists** for sub-elite altitude data (Boulder, Provo, Albuquerque, Air Force, El Paso). Endpoint cracked: `/list_data/<list_id>?event_type=<E>&gender=<m|f>&limit=500` with `Turbo-Frame: list_data` header. List IDs in `scrape_tfrrs.py` for years 2017-2024.

2. **WA biomechanics PDFs** for 10m splits (Berlin 2009 onwards) — would let us validate the v² coupling directly via measured velocity profiles instead of v_avg proxy.

3. **Iten/Eldoret athlete subsamples** as natural experiments on altitude adaptation — Kenyan/Ethiopian distance runners who train at altitude but race world records at sea level.
