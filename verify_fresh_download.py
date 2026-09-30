"""Rebuild the audit from a downloaded Kaggle ZIP in an isolated directory.

Reuses versioned code and the retrospective mass cache. Does not copy the old
race CSVs or optional indoor scrapes into the build. Compares outdoor records
because the supported audit excludes indoor races throughout.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def fingerprint(path):
    return dict(bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def compare_outdoor(reference, rebuilt):
    def records(path):
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            columns = tuple(sorted(reader.fieldnames))
            rows = list(reader)
        outdoor = Counter(tuple(r[c] for c in columns)
                          for r in rows if r["is_indoor"] == "0")
        return columns, outdoor, len(rows)
    ref_cols, ref, ref_n = records(reference)
    new_cols, new, new_n = records(rebuilt)
    return dict(reference_rows=ref_n, rebuilt_rows=new_n,
                reference_outdoor_rows=sum(ref.values()), rebuilt_outdoor_rows=sum(new.values()),
                columns_match=ref_cols == new_cols,
                outdoor_records_match=ref_cols == new_cols and ref == new,
                missing_outdoor_records=sum((ref - new).values()),
                extra_outdoor_records=sum((new - ref).values()),
                reference=fingerprint(reference), rebuilt=fingerprint(rebuilt))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "results/fresh_download.json")
    args = parser.parse_args()
    archive = args.archive.resolve()
    output = args.output.resolve()
    scratch = Path(tempfile.mkdtemp(prefix="track-altitude-fresh-"))
    print("Isolated build: " + str(scratch), flush=True)
    manifest = json.loads((ROOT / "DATA_PROVENANCE.json").read_text())
    comparisons = {}
    with zipfile.ZipFile(archive) as z:
        # Only explicitly selected members are read; no archive paths are trusted.
        for local_name, expected in manifest["local_archive_files"].items():
            member = str(Path(local_name).relative_to("archive_data"))
            if z.namelist().count(member) != 1:
                raise ValueError("Expected exactly one archive member: " + member)
            target = scratch / local_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
            actual = fingerprint(target)
            comparisons[member] = dict(**actual,
                matches_recorded_snapshot=actual["sha256"] == expected["sha256"],
                matches_current_local_file=actual == fingerprint(ROOT / local_name))
    print("Archive members matching recorded snapshot: " + str(sum(
        v["matches_recorded_snapshot"] for v in comparisons.values())) + "/" +
        str(len(comparisons)), flush=True)

    files = ["build_dataset_archive.py", "enrich_v3.py", "venues.py",
             "reproduce.py", "evaluation.py", "temporal_features.py",
             "anthropometrics.py", "probe_within_athlete_nationality.py",
             "athlete_anthro_cache.json", "requirements.txt", "tests/test_evaluation.py"]
    for name in files:
        target = scratch / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1")
    logs = []
    for script in ("build_dataset_archive.py", "enrich_v3.py", "reproduce.py"):
        print("Running " + script, flush=True)
        completed = subprocess.run([sys.executable, "-u", str(scratch / script)],
                                   cwd=str(scratch), env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logs.append(script + "\n" + completed.stdout)
        (scratch / "pipeline.log").write_text("\n".join(logs))
        if completed.returncode:
            raise RuntimeError(script + " failed; inspect " + str(scratch / "pipeline.log"))

    reference = json.loads((ROOT / "results/audit.json").read_text())
    fresh = json.loads((scratch / "results/audit.json").read_text())
    sections = ("sample", "protocol", "overlap", "temporal_base", "temporal_expanded", "career_support")
    section_matches = {key: fresh[key] == reference[key] for key in sections}
    derived = {name: compare_outdoor(ROOT / name, scratch / name)
               for name in ("dataset_all.csv", "dataset_v3.csv")}
    success = (all(v["matches_recorded_snapshot"] and v["matches_current_local_file"]
                   for v in comparisons.values()) and all(section_matches.values())
               and all(v["outdoor_records_match"] for v in derived.values()))
    report = dict(schema_version=1, passed=success,
        archive=fingerprint(archive),
        expected_source=manifest["dataset"]["url"],
        expected_version=manifest["dataset"]["displayed_version"],
        note="Archive bytes supplied via --archive; download origin is recorded in DATA_PROVENANCE.json. "
             "Fresh race-data rebuild using existing code, venue table, mass cache, and Python environment. "
             "Optional indoor scrapes omitted; outdoor records compared as multisets. "
             "Audit sections compared exactly, without numerical tolerance.",
        runner=fingerprint(Path(__file__).resolve()),
        reused_inputs={name: fingerprint(ROOT / name) for name in files},
        archive_members=comparisons, derived_datasets=derived,
        audit_sections_match=section_matches, fresh_audit=fresh,
        reference_audit=fingerprint(ROOT / "results/audit.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(passed=success, audit_sections_match=section_matches,
                         derived_datasets=derived), indent=2), flush=True)
    print("Report: " + str(output), flush=True)
    print("Build files and logs retained at " + str(scratch), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
