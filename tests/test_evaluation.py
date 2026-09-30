"""Guard evaluation boundaries and the statistical target, not just execution."""
import unittest
from datetime import date, timedelta

import numpy as np

from evaluation import date_folds, partial_fit, metrics
from temporal_features import best_in_window


class EvaluationTests(unittest.TestCase):
    def test_same_date_never_crosses_boundary(self):
        dates = np.repeat(np.arange(24), 3)
        seen = []
        for tr, te in date_folds(dates):
            self.assertLess(max(dates[tr]), min(dates[te]))
            self.assertFalse(set(tr) & set(te))
            seen.extend(te)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), set(range(12, 72)))

    def test_pb_excludes_same_day_and_future(self):
        today = date(2020, 1, 1)
        entries = [(today - timedelta(days=546), 8.),
                   (today - timedelta(days=545), 11.),
                   (today - timedelta(days=1), 12.), (today, 9.),
                   (today + timedelta(days=1), 7.)]
        self.assertEqual(best_in_window(entries, today), 11.)

    def test_future_changes_do_not_change_fitted_model(self):
        rng = np.random.RandomState(3)
        X = rng.normal(size=(500, 3))
        D = rng.normal(size=(500, 2))
        y = X[:, 0] + D[:, 0] * 2 + rng.normal(size=500) * .1
        tr, te = np.arange(400), np.arange(400, 500)
        first = partial_fit(X, y, D, tr, te)
        X[450:] += 10000; y[450:] -= 10000; D[450:] += 5000
        second = partial_fit(X, y, D, tr, te)
        np.testing.assert_allclose(first[0], second[0])
        np.testing.assert_allclose(first[1][:50], second[1][:50])
        np.testing.assert_allclose(first[2][:50], second[2][:50])

    def test_partialling_recovers_known_effect_with_confounding(self):
        rng = np.random.RandomState(12)
        X = rng.normal(size=(10000, 2))
        D = (3 * X[:, 0] + rng.normal(size=len(X)))[:, None]
        y = 4 * X[:, 0] + 2 * D[:, 0] + rng.normal(size=len(X)) * .1
        beta, _, _, _ = partial_fit(X, y, D, np.arange(8000), np.arange(8000, 10000))
        self.assertAlmostEqual(beta[0], 2., delta=.01)
        # Residualizing only y would underestimate the known effect.

    def test_sse_improvement_has_explicit_baseline(self):
        y = np.array([1., 2., 3.])
        self.assertEqual(metrics(y, y + 1, y)["relative_sse_improvement"], 1.)
        self.assertEqual(metrics(y, y + 1, y + 2)["relative_sse_improvement"], -3.)


if __name__ == "__main__":
    unittest.main()
