"""Corrected temporal prediction audit with PB-adjusted base controls.

Supersedes the historical V2 temporal script: includes log_pb, keeps dates
intact, fits preprocessing only on training rows, and reports improvement
against an explicit baseline. Run reproduce.py for saved evidence/provenance.
"""
import json
from evaluation import evaluate
from reproduce import load_rows


def main():
    rows, _ = load_rows()
    print(json.dumps(evaluate(rows), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
