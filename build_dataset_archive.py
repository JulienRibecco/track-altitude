"""Build dataset_all.csv from the WA archive dump (107k rows, 1958-2023).

Combines the archive's outdoor 100m/200m/400m with our scraped 60m indoor.
"""
from __future__ import annotations
import csv, re, sys
from datetime import datetime
from pathlib import Path
from collections import Counter

import venues as V

ARCHIVE = Path(__file__).parent / "archive_data"
RAW = Path(__file__).parent / "raw"
OUT = Path(__file__).parent / "dataset_all.csv"


def parse_mark(mark: str) -> float | None:
    m = re.match(r"^\s*([0-9]+[.:]?[0-9]+\.?[0-9]*)", mark)
    if not m:
        return None
    s = m.group(1)
    if ":" in s:
        m2 = re.match(r"^(\d+):(\d+\.\d+)$", s)
        if m2:
            return int(m2.group(1)) * 60 + float(m2.group(2))
    try:
        return float(s)
    except ValueError:
        return None


def parse_wind(wind: str) -> float | None:
    if wind is None or wind == "":
        return None
    w = wind.strip()
    if not w or w in ("-", "—"):
        return None
    try:
        return float(w)
    except ValueError:
        return None


def parse_date(d: str) -> str | None:
    if not d:
        return None
    d = d.strip()
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(d, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def archive_iter(distance: int, sex: str):
    """Yield rows from archive CSVs."""
    fname = ARCHIVE / sex / f"{distance}-metres.csv"
    if not fname.exists():
        return
    with open(fname) as f:
        for r in csv.DictReader(f):
            t = parse_mark(r["Mark"])
            if t is None:
                continue
            yield {
                "mark": r["Mark"],
                "wind": r.get("WIND", ""),
                "athlete": r["Competitor"],
                "country": r["Nat"],
                "pos": r["Pos"],
                "venue": r["Venue"],
                "date": r["Date"],
                "score": r.get("Results Score", ""),
                "_t": t,
            }


def scraped_iter(distance: int, sex: str, indoor: bool):
    """Yield rows from our scraped raw/ files (used for 60m indoor only)."""
    suffix = "_indoor" if indoor else ""
    fname = RAW / f"{distance}-metres_{sex}{suffix}.csv"
    if not fname.exists():
        return
    with open(fname) as f:
        for r in csv.DictReader(f):
            t = parse_mark(r["mark"])
            if t is None:
                continue
            yield {
                "mark": r["mark"], "wind": r["wind"],
                "athlete": r["athlete"], "country": r["country"],
                "pos": r["pos"], "venue": r["venue"],
                "date": r["date"], "score": r.get("score", ""),
                "_t": t,
            }


def main():
    rows_out = []
    seen = set()
    unresolved = Counter()

    sources = [
        # (distance, sex, is_indoor, source)
        (100,    "men",   False, "archive"),
        (200,    "men",   False, "archive"),
        (400,    "men",   False, "archive"),
        (800,    "men",   False, "archive"),
        (1500,   "men",   False, "archive"),
        (3000,   "men",   False, "archive"),
        (5000,   "men",   False, "archive"),
        (10000,  "men",   False, "archive"),
        (100,    "women", False, "archive"),
        (200,    "women", False, "archive"),
        (400,    "women", False, "archive"),
        (800,    "women", False, "archive"),
        (1500,   "women", False, "archive"),
        (3000,   "women", False, "archive"),
        (5000,   "women", False, "archive"),
        (10000,  "women", False, "archive"),
        (60,     "men",   True,  "scraped"),
        (60,     "women", True,  "scraped"),
    ]

    for dist, sex, is_indoor, source in sources:
        n_in = 0
        n_keep = 0
        iterator = (archive_iter(dist, sex) if source == "archive"
                    else scraped_iter(dist, sex, is_indoor))
        for r in iterator:
            n_in += 1
            d = parse_date(r["date"])
            w = parse_wind(r["wind"])
            sig = (r["athlete"], d, r["mark"], r["venue"], dist, sex)
            if sig in seen:
                continue
            seen.add(sig)
            elev, city, ctry = V.lookup(r["venue"])
            if elev is None:
                unresolved[(city, ctry)] += 1
            event = f"{dist}m"
            rows_out.append({
                "event": event, "distance_m": dist, "sex": sex,
                "is_indoor": int(is_indoor),
                "season": "indoor" if is_indoor else "outdoor",
                "time_s": r["_t"], "wind_ms": w, "altitude_m": elev,
                "city": city, "country_venue": ctry,
                "venue_raw": r["venue"],
                "athlete": r["athlete"], "country_athlete": r["country"],
                "date": d, "rank": "", "pos": r["pos"], "score": r["score"],
            })
            n_keep += 1
        print(f"  {source:>8s} {dist}m {sex} (indoor={is_indoor}): "
              f"{n_in} in -> {n_keep} kept")

    cols = ["event", "distance_m", "sex", "is_indoor", "season",
            "time_s", "wind_ms", "altitude_m",
            "city", "country_venue", "venue_raw",
            "athlete", "country_athlete", "date", "rank", "pos", "score"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)

    by = Counter((r["distance_m"], r["sex"]) for r in rows_out)
    by_high = Counter((r["distance_m"], r["sex"]) for r in rows_out
                      if r["altitude_m"] and r["altitude_m"] >= 1000)
    print(f"\nWrote {OUT} ({len(rows_out)} rows)")
    for k in sorted(by):
        print(f"  {k}: N={by[k]}, high-alt={by_high.get(k, 0)}")
    print(f"  unresolved venues: {sum(unresolved.values())} rows / "
          f"{len(unresolved)} cities")


if __name__ == "__main__":
    main()
