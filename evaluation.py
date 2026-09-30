"""Temporal prediction and partialling-out diagnostics; no causal identification.

All learned transforms fit on training rows. Date blocks keep same-day races
together. Fixed ridge regularization avoids tuning against future outcomes.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

EVENTS = (100, 200, 400, 800, 1500, 3000, 5000, 10000)
RIDGE_ALPHA = 1.0


def date_folds(dates, k=5):
    dates = np.asarray(dates)
    unique = np.unique(dates)
    if len(unique) < k + 1:
        raise ValueError("Need at least k+1 distinct dates")
    blocks = np.array_split(unique, k + 1)
    for block in blocks[1:]:
        yield (np.flatnonzero(dates < block[0]),
               np.flatnonzero((dates >= block[0]) & (dates <= block[-1])))


def design(rows, flexible=False):
    """Fixed schema; PB is included in both nuisance specifications."""
    fields = ["log_pb", "year", "doy", "wind"]
    cols = [np.array([r[f] for r in rows], float) for f in fields]
    if flexible:
        for f in ("v_avg", "v_peak_or_avg", "A", "mass"):
            cols.append(np.array([r[f] for r in rows], float))
        cols.extend([cols[0] ** 2, cols[4] ** 2, cols[5] ** 2,
                     cols[4] ** 2 / cols[6], cols[5] ** 2 / cols[6]])
    # Fixed categories do not learn a vocabulary from the held-out data.
    for event in EVENTS:
        for sex in (0, 1):
            if (event, sex) == (100, 0):
                continue
            cols.append(np.array([r["distance"] == event and
                                  r["is_women"] == sex for r in rows], float))
    X = np.column_stack(cols)
    y = np.array([r["log_y"] for r in rows])
    w = np.array([r["is_women"] for r in rows])
    drag = np.array([r["alt"] * r["v_avg"] ** 2 / r["A"] for r in rows])
    aerobic = np.array([r["alt"] * r["log_pb"] for r in rows])
    D = np.column_stack([drag, drag * w, aerobic, aerobic * w])
    return X, y, D


def partial_fit(X, y, D, train, test):
    """Residualize outcome AND exposures on the same training-only controls.

    This is regularized partialling-out, not exact OLS FWL. Inference would
    additionally require assumptions about confounding and dependence.
    """
    scaler = StandardScaler().fit(X[train])
    xtr = scaler.transform(X[train])
    xte = scaler.transform(X[test])
    nuisance = Ridge(alpha=RIDGE_ALPHA).fit(
        xtr, np.column_stack([y[train], D[train]]))
    rtr = np.column_stack([y[train], D[train]]) - nuisance.predict(xtr)
    means = nuisance.predict(xte)
    rte = np.column_stack([y[test], D[test]]) - means
    beta = np.linalg.lstsq(rtr[:, 1:], rtr[:, 0], rcond=None)[0]
    return beta, means[:, 0], means[:, 0] + rte[:, 1:] @ beta, rte


def coefficients(beta):
    a_d, d_d, a_o, d_o = map(float, beta)
    return dict(alpha_drag=a_d, delta_drag=d_d, alpha_aerobic=a_o,
                delta_aerobic=d_o,
                gamma_drag=d_d / a_d if abs(a_d) > 1e-12 else None,
                gamma_aerobic=d_o / a_o if abs(a_o) > 1e-12 else None)


def metrics(y, base, full):
    sse_base = float(np.sum((y - base) ** 2))
    sse_full = float(np.sum((y - full) ** 2))
    return {
        "rmse_log_baseline": float(np.sqrt(np.mean((y - base) ** 2))),
        "rmse_log_full": float(np.sqrt(np.mean((y - full) ** 2))),
        "relative_sse_improvement": 1 - sse_full / sse_base if sse_base else None,
    }


def evaluate(rows, flexible=False, k=5):
    X, y, D = design(rows, flexible=flexible)
    dates = np.array([r["date"] for r in rows])
    folds, residuals, truth, bases, predictions = [], [], [], [], []
    for number, (tr, te) in enumerate(date_folds(dates, k), 1):
        beta, base, pred, residual = partial_fit(X, y, D, tr, te)
        folds.append(dict(fold=number, n_train=len(tr), n_test=len(te),
                          train_start=str(min(dates[tr])), train_end=str(max(dates[tr])),
                          test_start=str(min(dates[te])), test_end=str(max(dates[te])),
                          **coefficients(beta), **metrics(y[te], base, pred)))
        residuals.append(residual)
        truth.append(y[te]); bases.append(base); predictions.append(pred)
    residual = np.concatenate(residuals)
    # This second-stage fit uses OOF rows for estimation, not a further test.
    beta = np.linalg.lstsq(residual[:, 1:], residual[:, 0], rcond=None)[0]
    return dict(
        controls="expanded" if flexible else "base", ridge_alpha=RIDGE_ALPHA,
        folds=folds, pooled_prediction=metrics(np.concatenate(truth),
            np.concatenate(bases), np.concatenate(predictions)),
        oof_partialling_coefficients=coefficients(beta),
        oof_residual_design_rank=int(np.linalg.matrix_rank(residual[:, 1:])),
        inference="Descriptive coefficients only; no causal or significance claim.")
