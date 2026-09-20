"""Focused checks for the shared statistical model helpers."""

import unittest

import numpy as np

from forecast_models import fit_smoothing, moving_average


class ForecastModelTests(unittest.TestCase):
    def test_recursive_moving_average(self):
        np.testing.assert_allclose(moving_average([1, 2, 3], 3, 3), [2, 7 / 3, 22 / 9])

    def test_multiplicative_smoothing_rejects_zero_history(self):
        with self.assertRaises(ValueError):
            fit_smoothing(
                np.tile([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0], 18),
                'HW multiplicative',
            )


if __name__ == '__main__':
    unittest.main()
