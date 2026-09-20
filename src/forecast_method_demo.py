"""Reproducible teaching examples, separate from the catalogue benchmark."""

import warnings
from html import escape
from io import StringIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from weekly_forecasts import MODELS, predict

DETAILS = {
    'Naive': (
        'Latest observed day',
        'Repeat that quantity for all seven future days.',
        'Cannot anticipate a trend or weekday pattern.',
    ),
    'Seasonal naive': (
        'Last seven observed days',
        'Repeat the last week in the same weekday order.',
        'Repeats unusual events from last week too.',
    ),
    'MA(7)': (
        'Last seven values',
        'Average seven values; append the prediction and repeat for the next day.',
        'Often lags behind a growing series.',
    ),
    'MA(14)': (
        'Last fourteen values',
        'Average fourteen values; later steps include earlier predictions.',
        'Smoother, but slower to respond to recent change.',
    ),
    'SES': (
        'Historical demand with learned recency weights',
        'Estimate a smoothed level and project it forward.',
        'No explicit trend or seasonal component.',
    ),
    'Holt': (
        'Historical demand levels and changes',
        'Estimate level and trend, then extend them into the forecast.',
        'Does not explicitly model a weekly pattern.',
    ),
    'HW additive': (
        'Level, trend and seven-day seasonal effects',
        'Combine a projected trend with an additive effect for each seasonal position.',
        'Assumes seasonal swings are roughly constant in size.',
    ),
    'HW multiplicative': (
        'Level, trend and seven-day seasonal factors',
        'Multiply the projected level and trend by seasonal factors.',
        'Requires positive history; assumes seasonal swings scale with level.',
    ),
    'ARIMA': (
        'Differenced demand and past model errors',
        'Demo ARIMA(1,1,1): difference once, then use one autoregressive and one error term.',
        'No explicit seven-day seasonal component in this demo.',
    ),
    'SARIMA': (
        'Seven-day differenced demand and past model errors',
        'Demo SARIMA(1,0,0)(0,1,1,7): use a daily autoregressive term and a seasonal error term after weekly differencing.',
        'Its chosen order can underfit or overfit; weekly seasonality must be useful.',
    ),
    'Linear regression': (
        '11 lag, rolling, time and weekday features',
        'Fit a weighted linear combination of the features to predict the next day.',
        'Feature relationships are linear; recursive errors can accumulate.',
    ),
    'Ridge(1)': (
        'Same 11 features as linear regression',
        'Fit a linear relationship with an L2 coefficient penalty; alpha = 1.',
        'Regularization can reduce unstable coefficients but also suppress useful effects.',
    ),
    'Ridge(10)': (
        'Same 11 features as linear regression',
        'Use a stronger L2 coefficient penalty; alpha = 10.',
        'Stronger regularization can underfit.',
    ),
    'Random forest': (
        'Same 11 engineered features',
        'Average 100 decision trees; maximum depth 5, minimum leaf size 5.',
        'Trees do not naturally extrapolate a rising trend beyond learned outcomes.',
    ),
    'Boosting(1)': (
        'Same 11 engineered features',
        'Sequentially fit 100 small trees to correct errors; L2 = 1.',
        'May fit patterns that do not persist; limited trend extrapolation.',
    ),
    'Boosting(10)': (
        'Same 11 engineered features',
        'Sequentially fit 100 small trees with stronger L2 regularization = 10.',
        'Stronger regularization may lose useful variation.',
    ),
}


def build_demo(horizon=7, predict_fn=predict):
    """Shared teaching layout; horizon and predictor are explicit inputs."""
    if horizon not in (7, 31):
        raise ValueError('Teaching horizon must be 7 or 31 days')
    scenarios = {
        'Steady demand': lambda t: 60 + 0 * t,
        'Growing demand': lambda t: 35 + 0.4 * t + 2.6 * np.maximum(t - 55, 0),
        'Weekly pattern': lambda t: 60 + 18 * np.sin(2 * np.pi * t / 7),
    }
    options = ''.join(f'<option>{escape(k)}</option>' for k in scenarios)
    models = ''.join(
        '<optgroup label="'
        + label
        + '">'
        + ''.join(f'<option value="{escape(m)}">{escape(m)}</option>' for m in group)
        + '</optgroup>'
        for label, group in [
            ('Classical Statistical Models', MODELS[:10]),
            ('Machine Learning Models', MODELS[10:]),
        ]
    )
    panels = []
    for scenario, curve in scenarios.items():
        t = np.arange(84)
        values = curve(t) + np.random.default_rng(42).normal(0, 3, len(t))
        history = pd.Series(values, index=pd.date_range('2023-01-01', periods=84))
        specs = {'ARIMA': ((1, 1, 1), (0, 0, 0, 0), 'n'), 'SARIMA': ((1, 0, 0), (0, 1, 1, 7), 'n')}
        for model in MODELS:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                forecast = (
                    predict_fn(history, model, specs)
                    if horizon == 7
                    else predict_fn(history, model, specs, horizon=horizon)
                )
            y_max = 180 if horizon == 7 else 280
            assert np.max(forecast) < y_max, 'Teaching chart would clip its forecast'
            fig, ax = plt.subplots(figsize=(12, 3.4), facecolor='white')
            ax.plot(
                np.arange(57, 85),
                values[-28:],
                color='#8993a4',
                label='Observed example demand',
                lw=1.7,
            )
            ax.axvspan(84.5, 84.5 + horizon, color='#0A66C2', alpha=0.07)
            ax.plot(
                np.arange(85, 85 + horizon),
                forecast,
                color='#0A66C2',
                marker='o',
                label=f'{horizon}-day forecast',
                lw=2,
            )
            ax.axvline(84.5, color='#8993a4', ls=':', lw=1)
            ax.set(xlabel='Example day', ylabel='Units', ylim=(0, y_max), xlim=(57, 85 + horizon))
            ax.spines[['top', 'right']].set_visible(False)
            ax.legend(loc='upper left', frameon=False, ncol=2)
            fig.tight_layout()
            buffer = StringIO()
            fig.savefig(buffer, format='svg')
            plt.close(fig)
            svg = buffer.getvalue()
            svg = svg[svg.index('<svg') :]
            inputs, method, limit = DETAILS[model]
            if model == 'Naive':
                method = f'Repeat that quantity for all {horizon} future days.'
            ml = model in MODELS[10:]
            if ml:
                inputs = 'Demand lags 1, 2, 3, 7 and 14; preceding 7/14-day means; 7-day standard deviation; time; weekday sine/cosine.'
                method += f' Predict one day, append that prediction, update the features and repeat through day {horizon}.'
                preparation = 'Demand is normalized using the training-history mean.'
                if model in ['Linear regression', 'Ridge(1)', 'Ridge(10)']:
                    preparation += ' Input features are also standardized using training data.'
            elif model in ['ARIMA', 'SARIMA']:
                preparation = 'These example orders are fixed for teaching; the project benchmark searches candidate orders.'
            elif model in ['SES', 'Holt', 'HW additive', 'HW multiplicative']:
                preparation = 'Smoothing parameters are estimated from the example history.'
            else:
                preparation = ''
            hidden = '' if scenario == 'Steady demand' and model == 'Naive' else ' hidden'
            extra = (
                f'<div><dt>Preparation</dt><dd>{escape(preparation)}</dd></div>'
                if preparation
                else ''
            )
            panels.append(
                f'<div class="method-demo-panel" data-scenario="{escape(scenario)}" data-model="{escape(model)}"{hidden}><dl class="method-explanation"><div><dt>Input data</dt><dd>{escape(inputs)}</dd></div><div><dt>How it forecasts</dt><dd>{escape(method)}</dd></div>{extra}<div><dt>Limitation</dt><dd>{escape(limit)}</dd></div></dl>{svg}</div>'
            )
    return (
        '<div class="method-demo"><div class="forecast-controls"><label>Demand pattern<select class="demo-scenario">'
        + options
        + '</select></label><label>Forecasting method<select class="demo-model">'
        + models
        + '</select></label></div>'
        + ''.join(panels)
        + '</div>'
    )
