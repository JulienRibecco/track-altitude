"""Descriptive nationality-composition sensitivity probe.

The hand-selected country set is a rough exposure proxy, not observed residence
or acclimatization. Per-career slopes control only a linear year trend. Legacy
precision weights and printed t-statistics assume ordinary regression errors;
they do not support confirmatory biological claims. reproduce.py reuses the
fits for support counts and descriptive slopes, omitting significance claims.

See WRITEUP.md for the current interpretation and explicit venue denominators.
"""
from __future__ import annotations
import csv, math
from pathlib import Path
from collections import defaultdict
from datetime import date as Date
import numpy as np

ROOT = Path(__file__).parent
DATA_ALL = ROOT / "dataset_all.csv"

# Nations whose elite distance runners predominantly live/train at altitude.
EAST_AFRICAN = {"KEN", "ETH", "ERI", "UGA", "TAN", "RWA", "BDI"}
# Common naturalization destinations for East African distance transfers.
EA_TRANSFER = {"BRN", "BHR", "QAT", "TUR", "KAZ", "AZE", "ROU"}
# High-altitude-capital nations in the Americas.
HIGH_ALT_AMERICAS = {"MEX", "COL", "ECU", "BOL", "PER"}
ALT_NATIVE = EAST_AFRICAN | EA_TRANSFER | HIGH_ALT_AMERICAS


def to_date(s):
    try:
        y, m, d = map(int, s.split("-")); return Date(y, m, d)
    except Exception:
        return None


def is_legal(wind_str, distance):
    if distance >= 400: return True
    if not wind_str: return False
    try: return abs(float(wind_str)) <= 2.0
    except ValueError: return False


def load_career_index(min_races=8, min_alt_races=2, min_alt_threshold=500.0):
    raw = defaultdict(list)
    country = {}
    with open(DATA_ALL) as f:
        for r in csv.DictReader(f):
            if int(r["is_indoor"]): continue
            try:
                dist = int(r["distance_m"]); t = float(r["time_s"])
                alt = float(r["altitude_m"]) if r["altitude_m"] else None
            except ValueError: continue
            if alt is None or t <= 1.5: continue
            if not is_legal(r["wind_ms"], dist): continue
            d = to_date(r["date"])
            if d is None: continue
            key = (r["athlete"], r["sex"], dist)
            raw[key].append((d, math.log(t), alt, d.year))
            country[(r["athlete"], r["sex"])] = r.get("country_athlete", "?")
    careers, cc = {}, {}
    for key, races in raw.items():
        if len(races) < min_races: continue
        if sum(1 for _, _, a, _ in races if a > min_alt_threshold) < min_alt_races:
            continue
        careers[key] = sorted(races)
        cc[key] = country[(key[0], key[1])]
    return careers, cc


def fit_per_athlete(careers, cc):
    results = []
    for (athlete, sex, dist), races in careers.items():
        n = len(races)
        log_t = np.array([r[1] for r in races])
        alt = np.array([r[2] for r in races])
        year_c = np.array([r[3] for r in races], float)
        year_c = year_c - year_c.mean()
        if alt.std() < 100: continue
        X = np.column_stack([np.ones(n), alt, year_c])
        try:
            beta, *_ = np.linalg.lstsq(X, log_t, rcond=None)
            resid = log_t - X @ beta
            sigma2 = (resid @ resid) / max(1, n - X.shape[1])
            se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
        except np.linalg.LinAlgError:
            continue
        if se[1] <= 0 or not math.isfinite(se[1]): continue
        results.append({
            "athlete": athlete, "sex": sex, "distance": dist, "n_races": n,
            "b_alt": beta[1], "se_b_alt": se[1],
            "country": cc[(athlete, sex, dist)],
            "alt_native": cc[(athlete, sex, dist)] in ALT_NATIVE,
        })
    return results


def agg(per, sex, dist, predicate=lambda r: True):
    rs = [r for r in per if r["sex"] == sex and r["distance"] == dist
          and predicate(r)]
    if not rs: return None
    b = np.array([r["b_alt"] for r in rs]); se = np.array([r["se_b_alt"] for r in rs])
    w = 1.0 / se**2
    return {"n": len(rs), "mean_b": float(np.sum(b*w)/np.sum(w)),
            "se": math.sqrt(1.0/np.sum(w)), "median": float(np.median(b))}


def cross_sex(per, dist, predicate, label):
    am = agg(per, "men", dist, predicate); aw = agg(per, "women", dist, predicate)
    if not am or not aw:
        print(f"  {label:<26} {dist:>6}m  insufficient (M={am['n'] if am else 0}, "
              f"W={aw['n'] if aw else 0})")
        return
    diff = aw["mean_b"] - am["mean_b"]
    se = math.sqrt(am["se"]**2 + aw["se"]**2)
    t = diff/se if se > 0 else 0
    ratio = aw["mean_b"]/am["mean_b"] if am["mean_b"] != 0 else float("nan")
    print(f"  {label:<26} {dist:>6}m  M:{am['n']:>3} {am['mean_b']:>+.2e}  "
          f"W:{aw['n']:>3} {aw['mean_b']:>+.2e}  Δ={diff:>+.2e}  t={t:>+5.2f}  "
          f"W/M={ratio:>5.2f}")


def main():
    print("=== Within-athlete sex×altitude: nationality/residence probe ===\n")
    careers, cc = load_career_index()
    per = fit_per_athlete(careers, cc)
    print(f"successful within-athlete fits: {len(per)}\n")

    dists = sorted({r["distance"] for r in per})
    print("Nationality-proxy composition by sex (not measured residence):")
    print(f"  {'event':>7}  {'M total':>8} {'M %native':>10}  "
          f"{'W total':>8} {'W %native':>10}")
    for d in dists:
        m = [r for r in per if r["sex"]=="men" and r["distance"]==d]
        w = [r for r in per if r["sex"]=="women" and r["distance"]==d]
        mp = np.mean([r["alt_native"] for r in m]) if m else float("nan")
        wp = np.mean([r["alt_native"] for r in w]) if w else float("nan")
        print(f"  {d:>7}  {len(m):>8} {mp:>10.0%}  {len(w):>8} {wp:>10.0%}")

    print("\n(A) ALL athletes  [replicate published result]:")
    for d in dists: cross_sex(per, d, lambda r: True, "all")

    print("\n(B) EXCLUDING altitude-native bloc  [the key test]:")
    for d in dists: cross_sex(per, d, lambda r: not r["alt_native"], "non-native only")

    print("\n(C) altitude-native bloc ONLY:")
    for d in dists: cross_sex(per, d, lambda r: r["alt_native"], "native only")

    print("\nDescriptive sensitivity only. Sparse subgroups cannot establish absence")
    print("of an effect. Nominal t-statistics do not account for shared meets or")
    print("between-athlete heterogeneity; persistence would not establish biology.")


if __name__ == "__main__":
    main()
