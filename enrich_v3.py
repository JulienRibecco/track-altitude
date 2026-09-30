"""Enrichment v3: athlete-agnostic features across all distances.

Per (event, sex) we still compute sea-level rolling SB and world rank
INDEPENDENTLY for each event (a 60m specialist isn't the same as a 400m specialist).

Then we collapse into a single tidy CSV with distance_m as a numeric column.
"""
from __future__ import annotations
import csv
from pathlib import Path
from datetime import date as Date
from collections import defaultdict
from bisect import insort

DATA = Path(__file__).parent / "dataset_all.csv"
OUT = Path(__file__).parent / "dataset_v3.csv"
SEA_LEVEL_MAX = 200.0


def to_date(s: str) -> Date | None:
    try:
        y, m, d = map(int, s.split("-"))
        return Date(y, m, d)
    except Exception:
        return None


def is_legal(wind_str: str | None, is_indoor: bool, distance: int | None = None) -> bool:
    if is_indoor:
        return True  # no wind indoors
    # 400m and longer have no wind reading (curve neutralizes wind effect)
    if distance is not None and distance >= 400:
        return True
    if wind_str is None or wind_str == "":
        return False
    try:
        return abs(float(wind_str)) <= 2.0
    except ValueError:
        return False


def load() -> list[dict]:
    rows = []
    with open(DATA) as f:
        for r in csv.DictReader(f):
            try:
                t = float(r["time_s"])
                a = float(r["altitude_m"]) if r["altitude_m"] else None
            except ValueError:
                continue
            d = to_date(r["date"])
            if d is None or a is None:
                continue
            r["_t"] = t
            r["_a"] = a
            r["_d"] = d
            r["_indoor"] = bool(int(r["is_indoor"]))
            r["_w"] = float(r["wind_ms"]) if r["wind_ms"] else None
            rows.append(r)
    return rows


def tier_of(rank: int) -> int:
    if rank <= 10: return 1
    if rank <= 50: return 2
    if rank <= 200: return 3
    return 4


# Years with Olympics (track held that calendar year)
OLYMPIC_YEARS = {2000, 2004, 2008, 2012, 2016, 2021, 2024}
# World Championships (Outdoor) calendar years
WORLDS_YEARS = {2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015,
                2017, 2019, 2022, 2023, 2025}


def enrich(rows: list[dict]) -> list[dict]:
    by_es: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_es[(r["event"], r["sex"])].append(r)

    out = []
    for key, grp in by_es.items():
        grp.sort(key=lambda r: r["_d"])
        ath_hist: dict[str, list[tuple[Date, float]]] = defaultdict(list)
        current_sb: dict[str, float] = {}
        # Per-athlete season tracking: races so far in current calendar year
        ytd_count: dict[str, int] = defaultdict(int)
        ytd_first_date: dict[str, Date] = {}
        ytd_year: dict[str, int] = {}

        for r in grp:
            d = r["_d"]
            cutoff = (Date(d.year - 1, d.month, d.day)
                      if not (d.month == 2 and d.day == 29)
                      else Date(d.year - 1, 2, 28))

            stale = [a for a, h in ath_hist.items() if h and h[0][0] < cutoff]
            for a in stale:
                ath_hist[a] = [(dd, tt) for dd, tt in ath_hist[a] if dd >= cutoff]
                if ath_hist[a]:
                    current_sb[a] = min(tt for _, tt in ath_hist[a])
                else:
                    current_sb.pop(a, None)

            ath = r["athlete"]
            sb = current_sb.get(ath)
            if sb is not None and current_sb:
                rank = 1 + sum(1 for a, s in current_sb.items()
                               if s < sb and a != ath)
                tier = tier_of(rank)
            else:
                rank = None
                tier = None

            # Season / peaking features (athlete-specific, year-resetting)
            ath = r["athlete"]
            if ytd_year.get(ath) != d.year:
                ytd_year[ath] = d.year
                ytd_count[ath] = 0
                ytd_first_date[ath] = d
            n_races_ytd = ytd_count[ath]  # PRE-race count
            if ath in ytd_first_date:
                weeks_since_first_ytd = (d - ytd_first_date[ath]).days / 7.0
            else:
                weeks_since_first_ytd = 0.0

            r["sl_sb_365"] = sb
            r["world_rank"] = rank
            r["tier"] = tier
            r["n_races_ytd"] = n_races_ytd
            r["weeks_since_first_ytd"] = round(weeks_since_first_ytd, 2)
            r["is_olympic_year"] = int(d.year in OLYMPIC_YEARS)
            r["is_worlds_year"] = int(d.year in WORLDS_YEARS)
            r["is_major_year"] = int(d.year in OLYMPIC_YEARS or d.year in WORLDS_YEARS)

            # Update season counter AFTER recording (so feature is pre-race)
            ytd_count[ath] += 1

            # Pre-race only update of history. Sea-level legal-wind only.
            sea_level = r["_a"] < SEA_LEVEL_MAX
            dist = int(r["distance_m"])
            if sea_level and is_legal(r["wind_ms"], r["_indoor"], dist):
                insort(ath_hist[ath], (d, r["_t"]))
                cur = current_sb.get(ath)
                if cur is None or r["_t"] < cur:
                    current_sb[ath] = r["_t"]

            if sb is not None:
                out.append(r)
    return out


def main():
    rows = load()
    print(f"Loaded {len(rows)} rows.")
    enriched = enrich(rows)
    print(f"With sl_sb_365 (≥1 prior sea-level legal race in same event): {len(enriched)}")

    cols = ["event", "distance_m", "sex", "is_indoor",
            "time_s", "wind_ms", "altitude_m",
            "sl_sb_365", "world_rank", "tier",
            "n_races_ytd", "weeks_since_first_ytd",
            "is_olympic_year", "is_worlds_year", "is_major_year",
            "city", "country_venue", "athlete", "country_athlete",
            "date", "rank", "score"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(enriched)
    print(f"Wrote {OUT}")

    by_es = defaultdict(int)
    by_es_high = defaultdict(int)
    for r in enriched:
        dist = int(r["distance_m"])
        if is_legal(r["wind_ms"], r["_indoor"], dist):
            k = (dist, r["sex"])
            by_es[k] += 1
            if r["_a"] >= 1000:
                by_es_high[k] += 1
    for k in sorted(by_es):
        print(f"  {k}: N={by_es[k]}, high-alt={by_es_high[k]}")


if __name__ == "__main__":
    main()
