"""Focused safeguards for hub grouping, recursive features and selection."""

import unittest

import numpy as np
import pandas as pd

from weekly_forecasts import TEST, VALIDATION, choose, feature_row, ml_forecast, proportional_groups


class HubTests(unittest.TestCase):
    def test_grouping_requires_bom_proportions(self):
        bom = pd.DataFrame(
            [(1, 'a', 1), (2, 'a', 2), (1, 'b', 3), (2, 'b', 6), (1, 'c', 1), (2, 'c', 3)],
            columns=['product_id', 'material_id', 'quantity_per_sale'],
        )
        result = proportional_groups(bom).set_index('material_id')
        self.assertEqual(result.loc['b', 'group_id'], 'a')
        self.assertEqual(result.loc['b', 'ratio'], 3)
        self.assertEqual(result.loc['c', 'group_id'], 'c')

    def test_features_use_only_available_history(self):
        history = np.arange(1, 31)
        row = feature_row(history, '2023-01-31', 30)
        self.assertEqual(row[:5], [30, 29, 28, 24, 17])
        self.assertEqual(row[5], np.mean(history[-7:]))

    def test_incomplete_model_cannot_win(self):
        rows = []
        for model, n, error in [('Naive', 28, 1), ('Ridge(1)', 27, 0)]:
            rows.extend(
                dict(model=model, origin=i // 7, actual=10, forecast=10 - error, scale=1)
                for i in range(n)
            )
        self.assertEqual(choose(pd.DataFrame(rows))['model'], 'Naive')

    def test_small_error_advantage_is_not_overridden(self):
        rows = []
        for model, error in [('Naive', 1.004), ('Ridge(1)', 1)]:
            rows.extend(
                dict(model=model, origin=i // 7, actual=10, forecast=10 - error, scale=1)
                for i in range(28)
            )
        self.assertEqual(choose(pd.DataFrame(rows))['model'], 'Ridge(1)')

    def test_new_ml_models_are_reproducible_and_finite(self):
        series = pd.Series(
            20 + np.sin(np.arange(70) * 2 * np.pi / 7) + np.arange(70) * 0.1,
            index=pd.date_range('2023-01-01', periods=70),
        )
        for model in ['Linear regression', 'Random forest']:
            first = ml_forecast(series, model)
            second = ml_forecast(series, model)
            self.assertEqual(first.shape, (7,))
            self.assertTrue(np.isfinite(first).all())
            self.assertTrue((first >= 0).all())
            np.testing.assert_allclose(first, second)

    def test_seven_day_windows_are_separate(self):
        def dates(origins):
            return {
                d
                for origin in origins
                for d in pd.date_range(pd.Timestamp(origin) + pd.Timedelta(days=1), periods=7)
            }

        validation = dates(VALIDATION)
        test = dates(TEST)
        self.assertEqual(len(validation), 28)
        self.assertEqual(len(test), 28)
        self.assertFalse(validation & test)
        self.assertLess(max(validation), min(test))


if __name__ == '__main__':
    unittest.main()
