"""Shared statistical helpers for the weekly and monthly benchmarks."""

import warnings

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

SEASON = 7


def moving_average(history, window, horizon=7):
    """Forecast recursively without inserting held-out observations."""
    values = list(np.asarray(history, dtype=float))
    forecast = []
    for _ in range(horizon):
        value = float(np.mean(values[-window:]))
        forecast.append(value)
        values.append(value)
    return np.asarray(forecast)


def fit_smoothing(history, name):
    """Fit SES, Holt, or seven-day Holt-Winters models."""
    history = np.asarray(history, dtype=float)
    if name == 'SES':
        model = SimpleExpSmoothing(history, initialization_method='estimated')
    elif name == 'Holt':
        model = Holt(history, initialization_method='estimated')
    else:
        seasonal = 'mul' if name == 'HW multiplicative' else 'add'
        if seasonal == 'mul' and np.any(history <= 0):
            raise ValueError('Multiplicative seasonality requires strictly positive history')
        model = ExponentialSmoothing(
            history,
            trend='add',
            seasonal=seasonal,
            seasonal_periods=SEASON,
            initialization_method='estimated',
        )
    result = model.fit(optimized=True, use_brute=False)
    if not result.mle_retvals.get('success', True):
        result = model.fit(optimized=True, use_brute=False, method='least_squares')
    return result


def differencing_order(history, seasonal=False):
    """Use a bounded ADF check to identify a differencing order."""
    values = np.asarray(history, dtype=float)
    if seasonal:
        values = values[SEASON:] - values[:-SEASON]
    max_d = 1 if seasonal else 2
    for d in range(max_d + 1):
        if (
            np.std(values) < 1e-10
            or adfuller(values, regression='c', autolag='AIC', result_object=False)[1] < 0.05
        ):
            return d
        values = np.diff(values)
    return max_d


def fit_arima(history, order, seasonal_order=(0, 0, 0, 0), trend='n'):
    """Fit an ARIMA/SARIMA model with constrained state-space likelihood."""
    model = SARIMAX(
        np.asarray(history),
        order=order,
        seasonal_order=seasonal_order,
        trend=trend,
        enforce_stationarity=True,
        enforce_invertibility=True,
    )
    result = model.fit(disp=False, maxiter=150)
    if not result.mle_retvals.get('converged', True):
        result = model.fit(disp=False, method='powell', maxiter=300)
    return result


def identify_arima(history, family):
    """Compare a small declared ARIMA or SARIMA grid using AIC."""
    d = differencing_order(history, seasonal=family == 'SARIMA')
    if family == 'ARIMA':
        candidates = [
            ((p, d, q), (0, 0, 0, 0), trend)
            for p, q in [(0, 0), (1, 0), (0, 1), (1, 1)]
            for trend in (['n', 'c'] if d < 2 else ['n'])
        ]
    else:
        candidates = [
            ((p, d, q), (p_seasonal, 1, q_seasonal, SEASON), 'n')
            for p, q, p_seasonal, q_seasonal in [
                (0, 0, 0, 1),
                (0, 0, 1, 0),
                (1, 0, 0, 1),
                (0, 1, 0, 1),
            ]
        ]
    fits = []
    records = []
    for order, seasonal_order, trend in candidates:
        try:
            with warnings.catch_warnings(record=True):
                result = fit_arima(history, order, seasonal_order, trend)
            converged = bool(result.mle_retvals.get('converged', True))
            valid = converged and np.isfinite(result.aic)
            records.append(
                {
                    'family': family,
                    'order': str(order),
                    'seasonal_order': str(seasonal_order),
                    'trend': trend,
                    'aic': result.aic,
                    'bic': result.bic,
                    'converged': converged,
                }
            )
            if valid:
                fits.append((result.aic, (order, seasonal_order, trend)))
        except (ValueError, np.linalg.LinAlgError) as error:
            records.append(
                {
                    'family': family,
                    'order': str(order),
                    'seasonal_order': str(seasonal_order),
                    'trend': trend,
                    'aic': np.nan,
                    'bic': np.nan,
                    'converged': False,
                    'error': str(error),
                }
            )
    if not fits:
        return None, records
    return min(fits, key=lambda item: item[0])[1], records
