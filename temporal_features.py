"""Past-only race-history feature pipeline with retrospective mass proxies.

For each race at date d, race-history features use only dates < d.
Mass lookups are static retrospective proxies, not date-stamped measurements.
This prevents future race-result leakage; it does not establish causality or
simulate the historical availability of every covariate.

Features built:
  log_pb         — best PB in [d-545, d), past-only (already past-only in
                   pre-existing code, just made explicit here).
  v_avg          — distance / pb. Past-only by construction.
  v_peak_strict  — 100 / (pb_200 - pb_100) where BOTH pb_100 and pb_200 must
                   be set before d. Returns None if either missing.
  rolling_tier   — within (event, sex) cohort, athlete's percentile rank as
                   of d (using each cohort-member's best PB before d).
                   Computed annually for efficiency; tier shifts gradually.
  A_athlete      — country-mean fallback unless Phase A scrape resolved this
                   athlete; static across time, an approximation that is not verified
                   for each athlete or era.

Static features (no date dependence): alt, year, doy, distance, country,
is_women, mass (lookup table or athlete cache).

Future-leak audit:
  v_peak: previously used cv_w_per_athlete.json which was fit on FULL career
          PBs — leak. Fixed via best_in_window with both PBs constrained.
  tier:   previously used career-best percentile — leak. Fixed via annual
          rolling cohort.
  CP fits (CV, W'): not yet temporal-aware. Skip for now; would require
          per-(athlete, race) refit. Defer to follow-up.
"""
from __future__ import annotations
import csv, json, math
from pathlib import Path
from collections import defaultdict
from datetime import date as Date, timedelta
import numpy as np

from anthropometrics import lookup, area_proxy

ROOT = Path(__file__).parent
DATA_V3 = ROOT / "dataset_v3.csv"
DATA_ALL = ROOT / "dataset_all.csv"
ANTHRO_CACHE = ROOT / "athlete_anthro_cache.json"
SEA_LEVEL_MAX = 200.0
PB_WINDOW_DAYS = 545


def to_date(s):
    try:
        y, m, d = map(int, s.split("-"))
        return Date(y, m, d)
    except Exception:
        return None


def is_legal(wind_str, distance):
    if distance >= 400: return True
    if not wind_str: return False
    try: return abs(float(wind_str)) <= 2.0
    except ValueError: return False


def build_pb_log() -> dict:
    """{distance: {(athlete, sex): [(date, time), ...]}} sorted by date."""
    log = defaultdict(lambda: defaultdict(list))
    with open(DATA_ALL) as f:
        for r in csv.DictReader(f):
            if int(r["is_indoor"]): continue
            try:
                dist = int(r["distance_m"]); t = float(r["time_s"])
                a = float(r["altitude_m"]) if r["altitude_m"] else None
            except ValueError: continue
            if a is None or a >= SEA_LEVEL_MAX: continue
            if not is_legal(r["wind_ms"], dist): continue
            d = to_date(r["date"])
            if d is None: continue
            log[dist][(r["athlete"], r["sex"])].append((d, t))
    for dist in log:
        for k in log[dist]:
            log[dist][k].sort()
    return log


def best_in_window(entries, race_date, window_days=PB_WINDOW_DAYS):
    """Best (lowest) time in [race_date - window_days, race_date) — strictly past."""
    if entries is None: return None
    earliest = race_date - timedelta(days=window_days)
    best = None
    for d, t in entries:
        if d >= race_date: break  # strict <, not <=
        if d < earliest: continue
        if best is None or t < best: best = t
    return best


_DISTANCE_LADDER = [100, 200, 400, 800, 1500, 3000, 5000, 10000]


def v_peak_strict(pb_log, athlete_key, race_date, window_days=PB_WINDOW_DAYS):
    """Best estimate of athlete's peak velocity given available past PBs.

    Preference order (best peak-v proxy first):
      1. From (100m, 200m) PB pair: v_peak = 100 / (pb_200 - pb_100)
         — averages the second 100m of a 200m race, ≈ true peak v.
      2. Fallback: v_avg of athlete's shortest-available PB (closer to peak v
         than longer-distance v_avg; 200m race v ≈ 9.0 m/s for elite men, vs
         5000m race v ≈ 5.7 m/s — shortest is always closer to peak).
    Returns None only if athlete has NO past PBs at any distance.
    """
    pb_100 = best_in_window(pb_log.get(100, {}).get(athlete_key), race_date, window_days)
    pb_200 = best_in_window(pb_log.get(200, {}).get(athlete_key), race_date, window_days)
    if pb_100 is not None and pb_200 is not None and pb_200 > pb_100:
        return 100.0 / (pb_200 - pb_100)
    # fallback: shortest-available PB's v_avg
    for d in _DISTANCE_LADDER:
        pb = best_in_window(pb_log.get(d, {}).get(athlete_key), race_date, window_days)
        if pb is not None:
            return d / pb
    return None


def build_rolling_tier_index(pb_log: dict, year_window: int = 2):
    """Pre-compute per-(event, sex, year) cohort percentile thresholds.

    For each (event, sex, year):
      cohort = athletes with best PB in [year - window, year) — strictly past
      thresholds at 33% and 67% percentile of cohort PBs

    Returns: {(distance, sex, year): (t1_threshold, t2_threshold, n_cohort)}
    where t1 = 33rd percentile (fastest 1/3 ≤ this), t2 = 67th percentile.
    """
    # Collect all (event, sex, year) tuples we'll need from training data
    years_per_es = defaultdict(set)
    for dist, by_ath in pb_log.items():
        for ath_key, entries in by_ath.items():
            for d, t in entries:
                years_per_es[(dist, ath_key[1])].add(d.year)

    index = {}
    for (dist, sex), years in years_per_es.items():
        for year in years:
            year_start = Date(year, 1, 1)
            window_start = Date(year - year_window, 1, 1)
            cohort_pbs = []
            for ath_key, entries in pb_log[dist].items():
                if ath_key[1] != sex: continue
                # best PB strictly before year_start, within rolling window
                best = None
                for d, t in entries:
                    if d >= year_start: break
                    if d < window_start: continue
                    if best is None or t < best: best = t
                if best is not None:
                    cohort_pbs.append(best)
            if len(cohort_pbs) < 10:
                continue  # cohort too small, leave undefined
            cohort_pbs.sort()
            n = len(cohort_pbs)
            t1 = cohort_pbs[n // 3]
            t2 = cohort_pbs[2 * n // 3]
            index[(dist, sex, year)] = (t1, t2, n)
    return index


def rolling_tier_lookup(tier_index, distance, sex, race_date, athlete_pb):
    """Return tier 1/2/3 for athlete_pb in (distance, sex) cohort as of race_date.
    Uses thresholds for race_date.year (cohort = past 2 years before that year).
    Returns None if cohort undefined or athlete_pb is None."""
    if athlete_pb is None:
        return None
    key = (distance, sex, race_date.year)
    if key not in tier_index:
        return None
    t1, t2, n = tier_index[key]
    if athlete_pb <= t1:
        return 1
    elif athlete_pb <= t2:
        return 2
    else:
        return 3


def load_temporal_rows(pb_log, anthro_cache, tier_index):
    """Load past race history and static mass proxies from the enriched sample."""
    rows = []
    n_v_peak_resolved = 0
    n_tier_resolved = 0
    with open(DATA_V3) as f:
        for r in csv.DictReader(f):
            if int(r["is_indoor"]): continue
            try:
                dist = int(r["distance_m"]); t = float(r["time_s"])
                alt = float(r["altitude_m"]) if r["altitude_m"] else None
            except ValueError: continue
            if alt is None: continue
            if not is_legal(r["wind_ms"], dist): continue
            d = to_date(r["date"])
            if d is None: continue
            athlete_key = (r["athlete"], r["sex"])
            entries = pb_log.get(dist, {}).get(athlete_key)
            pb = best_in_window(entries, d, PB_WINDOW_DAYS)
            if pb is None or pb <= 1.5: continue
            wind = float(r["wind_ms"]) if r["wind_ms"] else 0.0
            v_avg = dist / pb
            ctry = r["country_athlete"]
            mass_ctry, _, _ = lookup(ctry, r["sex"], dist)
            ckey = f"{r['athlete']}|{ctry}|{r['sex']}"
            anthro = anthro_cache.get(ckey)
            mass = anthro.get("mass_kg") if anthro and anthro.get("mass_kg") else mass_ctry
            A = area_proxy(mass)

            # Strict-temporal v_peak (now with shortest-PB fallback)
            vp = v_peak_strict(pb_log, athlete_key, d)
            if vp is not None:
                n_v_peak_resolved += 1
            # Track whether the (100, 200) pair produced v_peak
            pb_100 = best_in_window(pb_log.get(100, {}).get(athlete_key), d, PB_WINDOW_DAYS)
            pb_200 = best_in_window(pb_log.get(200, {}).get(athlete_key), d, PB_WINDOW_DAYS)
            from_100_200 = (pb_100 is not None and pb_200 is not None and pb_200 > pb_100)

            # Rolling tier
            tier = rolling_tier_lookup(tier_index, dist, r["sex"], d, pb)
            if tier is not None:
                n_tier_resolved += 1

            rows.append({
                "date": d, "year": d.year, "doy": d.timetuple().tm_yday,
                "log_y": math.log(t), "log_pb": math.log(pb), "pb": pb,
                "alt": alt, "wind": wind,
                "is_women": int(r["sex"] == "women"),
                "distance": dist, "v_avg": v_avg, "A": A, "mass": mass,
                "v_peak_strict": vp,                      # None only if athlete has zero prior PBs
                "v_peak_or_avg": vp if vp is not None else v_avg,
                "has_v_peak": int(vp is not None),
                "v_peak_from_sprint_pair": int(from_100_200),
                "tier_rolling": tier,                     # None if cohort undefined
                "country": ctry,
            })
    print(f"  loaded {len(rows)} rows")
    print(f"  v_peak_strict resolved: {n_v_peak_resolved}/{len(rows)} "
          f"({100*n_v_peak_resolved/len(rows):.1f}%)")
    print(f"  rolling_tier resolved:  {n_tier_resolved}/{len(rows)} "
          f"({100*n_tier_resolved/len(rows):.1f}%)")
    return rows


def main_demo():
    """Smoke test the pipeline."""
    print("Building PB log…")
    pb_log = build_pb_log()
    print(f"  {sum(len(v) for v in pb_log.values())} (event, athlete) entries")

    print("Loading anthro cache…")
    anthro_cache = json.loads(ANTHRO_CACHE.read_text()) if ANTHRO_CACHE.exists() else {}
    print(f"  {len(anthro_cache)} athletes")

    print("Building rolling tier index (annual)…")
    tier_index = build_rolling_tier_index(pb_log, year_window=2)
    print(f"  {len(tier_index)} (event, sex, year) cells with defined tier")

    print("\nLoading temporal rows…")
    rows = load_temporal_rows(pb_log, anthro_cache, tier_index)

    # Sanity: distribution of v_peak coverage by event
    from collections import Counter
    by_event_vp = defaultdict(lambda: [0, 0])
    for r in rows:
        by_event_vp[r["distance"]][1] += 1
        if r["has_v_peak"]: by_event_vp[r["distance"]][0] += 1
    print(f"\n  v_peak coverage by event:")
    for d in sorted(by_event_vp):
        v, n = by_event_vp[d]
        print(f"    {d:>5d}m: {v}/{n} ({100*v/n:.1f}%)")

    # Sanity: tier coverage by year
    by_year_tier = defaultdict(lambda: [0, 0])
    for r in rows:
        by_year_tier[r["year"]][1] += 1
        if r["tier_rolling"] is not None: by_year_tier[r["year"]][0] += 1
    yrs = sorted(by_year_tier)
    print(f"\n  rolling tier coverage by year (sample):")
    for y in [yrs[0], yrs[len(yrs)//4], yrs[len(yrs)//2], yrs[3*len(yrs)//4], yrs[-1]]:
        v, n = by_year_tier[y]
        print(f"    {y}: {v}/{n} ({100*v/n:.1f}%)")

    return rows


if __name__ == "__main__":
    main_demo()
