"""Calendar-month coverage, causal prediction and independent result checks."""

import hashlib
import json
import unittest

import numpy as np
import pandas as pd

from monthly_forecasts import MODELS, OUT, ROOT, TEST, VALIDATION, choose, predict


class MonthlyTests(unittest.TestCase):
    def test_monthly_baseline_repeats_last_observed_week(self):
        history = pd.Series(np.arange(1.0, 85.0), index=pd.date_range('2023-01-01', periods=84))
        for horizon in (30, 31):
            np.testing.assert_array_equal(
                predict(history, 'Seasonal naive', {}, horizon),
                np.resize(history.values[-7:], horizon),
            )
            self.assertEqual(len(predict(history, 'MA(7)', {}, horizon)), horizon)

    def test_ml_prefix_is_independent_of_requested_horizon(self):
        history = pd.Series(
            30 + np.arange(84) * 0.3 + np.sin(np.arange(84)),
            index=pd.date_range('2023-01-01', periods=84),
        )
        for model in MODELS[10:]:
            short = predict(history, model, {}, 7)
            long = predict(history, model, {}, 31)
            np.testing.assert_allclose(long[:7], short)
            self.assertTrue(np.isfinite(long).all())
            self.assertTrue((long >= 0).all())

    def test_incomplete_may_candidate_cannot_win(self):
        rows = [
            dict(model=m, actual=10, forecast=f, scale=1)
            for m, n, f in [('Naive', 31, 9), ('Ridge(1)', 30, 10)]
            for _ in range(n)
        ]
        self.assertEqual(choose(pd.DataFrame(rows))['model'], 'Naive')

    def test_small_mse_advantage_wins(self):
        rows = [
            dict(model=m, actual=10, forecast=10 - error, scale=1)
            for m, error in [('Naive', 1.004), ('Ridge(1)', 1)]
            for _ in range(31)
        ]
        self.assertEqual(choose(pd.DataFrame(rows))['model'], 'Ridge(1)')

    def test_outputs_and_selection_reconcile(self):
        manifest = json.loads((OUT / 'experiment.json').read_text())
        for path, digest in manifest['input_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        for path, digest in manifest['output_hashes'].items():
            self.assertEqual(hashlib.sha256((OUT / path).read_bytes()).hexdigest(), digest)
        frames = pd.read_csv(OUT / 'forecasts.csv')
        self.assertEqual(VALIDATION, ['2023-04-30'])
        self.assertEqual(TEST, ['2023-05-31'])
        for split, n, last in [('validation', 31, '2023-05-31'), ('test', 30, '2023-06-30')]:
            f = frames[frames.split.eq(split)]
            self.assertEqual(f.date.max(), last)
            self.assertTrue(f.groupby(['group_id', 'model']).size().eq(n).all())
            self.assertTrue((f.date > f.origin).all())
        selections = pd.read_csv(OUT / 'selection.csv').query("scope == 'all'")
        self.assertEqual(len(selections), 61)
        for row in selections.itertuples():
            validation = frames[frames.split.eq('validation') & frames.group_id.eq(row.group_id)]
            self.assertEqual(choose(validation)['model'], row.model)
        items = pd.read_csv(OUT / 'item_july_forecasts.csv')
        groups = pd.read_csv(OUT / 'july_forecasts.csv')
        self.assertEqual(len(items), 64 * 31)
        self.assertEqual(len(groups), 61 * 31)
        self.assertFalse(items.duplicated(['material_id', 'date']).any())
        merged = items.merge(
            groups[['group_id', 'date', 'forecast']],
            on=['group_id', 'date'],
            suffixes=('_item', '_group'),
        )
        np.testing.assert_allclose(merged.forecast_item, merged.forecast_group * merged.ratio)


if __name__ == '__main__':
    unittest.main()
