"""Corrected temporal partialling-out diagnostic with expanded controls.

Supersedes the historical reverse-residualization experiment. Outcome and
altitude basis columns are now residualized on the same controls using
training-only fits. Ridge means this is not the exact OLS FWL identity.
OOF coefficients are descriptive estimates, not an independent test of those
coefficients and not a causal effect. See WRITEUP.md for limitations.
"""
import json
from evaluation import evaluate
from reproduce import load_rows


def main():
    rows, _ = load_rows()
    print(json.dumps(evaluate(rows, flexible=True), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
