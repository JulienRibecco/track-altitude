"""Run the supported audit from local inputs and save aggregate evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import scipy
import sklearn
import joblib
import threadpoolctl

from evaluation import evaluate
from temporal_features import build_pb_log, load_temporal_rows
from probe_within_athlete_nationality import load_career_index, fit_per_athlete

ROOT = Path(__file__).resolve().parent


def fingerprint(path):
    return {"bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def load_rows():
    required = ["dataset_all.csv", "dataset_v3.csv", "athlete_anthro_cache.json"]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing local inputs: " + ", ".join(missing) +
                                ". See README.md, Data and reproduction.")
    pb_log = build_pb_log()
    cache = json.loads((ROOT / "athlete_anthro_cache.json").read_text())
    # Neither audited model uses tier. Avoid computing an unused feature.
    rows = load_temporal_rows(pb_log, cache, {})
    return sorted(rows, key=lambda r: r["date"]), required


def overlap(rows):
    result = []
    for event in sorted({r["distance"] for r in rows}):
        groups = [[r["pb"] for r in rows if r["distance"] == event and
                   r["is_women"] == sex] for sex in (0, 1)]
        if not all(groups):
            continue
        lo, hi = max(map(min, groups)), min(map(max, groups))
        result.append(dict(event=event, men_n=len(groups[0]), women_n=len(groups[1]),
                           men_max_pb=max(groups[0]), women_min_pb=min(groups[1]),
                           intersecting_range=lo <= hi,
                           rows_in_shared_range=sum(lo <= p <= hi for g in groups for p in g)))
    return result


def career_support():
    careers, countries = load_career_index()
    per = fit_per_athlete(careers, countries)
    composition = []
    for event in sorted({r["distance"] for r in per}):
        for sex in ("men", "women"):
            subset = [r for r in per if r["distance"] == event and r["sex"] == sex]
            if not subset:
                continue
            slopes = np.array([r["b_alt"] for r in subset])
            weights = np.array([1 / r["se_b_alt"] ** 2 for r in subset])
            composition.append(dict(event=event, sex=sex, n=len(subset),
                nationality_proxy_n=sum(r["alt_native"] for r in subset),
                weighted_slope=float(np.average(slopes, weights=weights)),
                median_slope=float(np.median(slopes))))
    # Explicit denominator: outdoor 5000m races in qualifying proxy-positive
    # careers. Unknown venue countries remain unknown, never counted as away.
    qualified = {(r["athlete"], r["sex"], r["distance"])
                 for r in per if r["distance"] == 5000 and r["alt_native"]}
    venues = {band: dict(home=0, away=0, unknown=0)
              for band in ("below_200m", "200_to_500m", "above_500m")}
    with (ROOT / "dataset_all.csv").open() as f:
        for r in csv.DictReader(f):
            key = (r["athlete"], r["sex"], int(r["distance_m"]))
            if key not in qualified or int(r["is_indoor"]) or not r["altitude_m"]:
                continue
            alt = float(r["altitude_m"])
            band = "below_200m" if alt < 200 else "above_500m" if alt > 500 else "200_to_500m"
            known = r["country_venue"] and r["country_athlete"]
            kind = "unknown" if not known else "home" if r["country_venue"] == r["country_athlete"] else "away"
            venues[band][kind] += 1
    return dict(qualifying_careers=len(per), composition=composition,
                venue_counts_5000m_proxy_positive=venues,
                caveat="Nationality proxy is not measured residence or acclimatization. "
                       "Weighted slopes use legacy within-career OLS precision; no inferential intervals.")


def run(output):
    rows, required = load_rows()
    print("Evaluating base controls…", flush=True)
    base = evaluate(rows)
    print("Evaluating expanded controls…", flush=True)
    expanded = evaluate(rows, flexible=True)
    print("Auditing support…", flush=True)
    sources = ["reproduce.py", "evaluation.py", "temporal_features.py",
               "anthropometrics.py", "probe_within_athlete_nationality.py",
               "requirements.txt", "tests/test_evaluation.py"]
    result = dict(schema_version=1,
        environment=dict(python=platform.python_version(), numpy=np.__version__,
                         scipy=scipy.__version__, scikit_learn=sklearn.__version__,
                         joblib=joblib.__version__, threadpoolctl=threadpoolctl.__version__),
        inputs={name: fingerprint(ROOT / name) for name in required},
        sources={name: fingerprint(ROOT / name) for name in sources},
        sample=dict(n=len(rows), first_date=str(rows[0]["date"]),
                    last_date=str(rows[-1]["date"])),
        protocol="Five expanding windows over six blocks of unique dates. "
                 "Rolling prediction with past race history; static retrospective mass proxies. "
                 "Fixed ridge alpha=1. No test-driven tuning. Corrected audit is exploratory.",
        overlap=overlap(rows), temporal_base=base, temporal_expanded=expanded,
        career_support=career_support())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Saved " + str(output), flush=True)
    for spec in (base, expanded):
        print(spec["controls"], spec["pooled_prediction"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "audit.json")
    run(parser.parse_args().output)
