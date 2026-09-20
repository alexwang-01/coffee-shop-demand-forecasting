"""Hub-level rolling forecasts with BOM-proven proportional groups."""

import os

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import hashlib
import json
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from forecast_models import fit_arima, fit_smoothing, identify_arima, moving_average

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/monthly'
VALIDATION = ['2023-04-30']
TEST = ['2023-05-31']
MODELS = [
    'Naive',
    'Seasonal naive',
    'MA(7)',
    'MA(14)',
    'SES',
    'Holt',
    'HW additive',
    'HW multiplicative',
    'ARIMA',
    'SARIMA',
    'Linear regression',
    'Ridge(1)',
    'Ridge(10)',
    'Random forest',
    'Boosting(1)',
    'Boosting(10)',
]
POLICY = {
    'horizon': 'next calendar month',
    'validation_days': 31,
    'test_days': 30,
    'july_days': 31,
    'training_end': '2023-04-30',
    'validation_origins': VALIDATION,
    'test_origins': TEST,
    'models': MODELS,
    'selection': 'Complete 31-day May validation; choose lowest MSE. Exact ties use alphabetical model name for reproducibility only.',
    'arima_identification': 'Jan-Apr only; bounded AIC grid, orders frozen thereafter',
    'ml_features': 'lags 1,2,3,7,14; previous 7/14-day mean and 7-day standard deviation; linear time and weekday sine/cosine. Recursive calendar-month forecast (30 or 31 days).',
    'boosting': {
        'max_iter': 100,
        'max_depth': 3,
        'min_samples_leaf': 10,
        'learning_rate': 0.05,
        'early_stopping': False,
        'random_state': 42,
    },
    'random_forest': {
        'n_estimators': 100,
        'max_depth': 5,
        'min_samples_leaf': 5,
        'random_state': 42,
        'n_jobs': 1,
    },
    'evaluation': 'Retrospective; June was viewed previously. All May and June dates scored. Only one validation month and one test month; selection stability is uncertain.',
}


def proportional_groups(bom):
    matrix = bom.pivot(
        index='product_id', columns='material_id', values='quantity_per_sale'
    ).fillna(0)
    groups, rows = [], []
    for item in matrix.columns:
        vector = matrix[item].to_numpy()
        match = None
        for representative, reference in groups:
            position = np.flatnonzero(reference)[0]
            ratio = vector[position] / reference[position]
            if ratio > 0 and np.allclose(vector, reference * ratio, rtol=1e-10, atol=1e-12):
                match = (representative, ratio)
                break
        if match is None:
            groups.append((item, vector))
            match = (item, 1.0)
        rows.append({'material_id': item, 'group_id': match[0], 'ratio': match[1]})
    return pd.DataFrame(rows)


def prepare():
    config = json.loads((ROOT / 'config/experiment.json').read_text())
    source = (ROOT / config['source']).resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config['source_sha256']
    sales = pd.read_excel(source)
    bom = pd.read_csv(ROOT / 'data/assumptions/bom.csv')
    materials = pd.read_csv(ROOT / 'data/assumptions/materials.csv')
    assert not bom.duplicated(['product_id', 'material_id']).any()
    assert materials.material_id.is_unique and bom.quantity_per_sale.gt(0).all()
    assert set(sales.product_id) == set(bom.product_id)
    assert set(bom.material_id) == set(materials.material_id)
    assert sales.transaction_qty.gt(0).all() and not sales.isna().any().any()
    sales['date'] = pd.to_datetime(sales.transaction_date).dt.normalize()
    product_daily = (
        sales.groupby(['date', 'product_id']).transaction_qty.sum().unstack(fill_value=0)
    )
    calendar = pd.date_range(sales.date.min(), sales.date.max(), freq='D')
    assert sales.groupby('store_id').date.nunique().eq(len(calendar)).all()
    matrix = bom.pivot(
        index='product_id', columns='material_id', values='quantity_per_sale'
    ).fillna(0)
    daily = product_daily.reindex(index=calendar, columns=matrix.index, fill_value=0).dot(matrix)
    daily.index.name = 'date'
    groups = proportional_groups(bom).merge(materials, on='material_id', validate='one_to_one')
    for row in groups.itertuples():
        np.testing.assert_allclose(daily[row.material_id], daily[row.group_id] * row.ratio)
    return daily, groups


def feature_row(history, date, position):
    values = np.asarray(history)
    weekday = pd.Timestamp(date).dayofweek
    return [values[-lag] for lag in [1, 2, 3, 7, 14]] + [
        values[-7:].mean(),
        values[-14:].mean(),
        values[-7:].std(),
        position / 181,
        np.sin(2 * np.pi * weekday / 7),
        np.cos(2 * np.pi * weekday / 7),
    ]


def ml_forecast(history, model, horizon=31):
    scale = max(float(history.mean()), 1e-8)
    normalized = history.to_numpy() / scale
    X = [feature_row(normalized[:i], history.index[i], i) for i in range(14, len(history))]
    y = normalized[14:]
    if model == 'Linear regression':
        estimator = make_pipeline(StandardScaler(), LinearRegression())
    elif model == 'Random forest':
        estimator = RandomForestRegressor(**POLICY['random_forest'])
    elif model.startswith('Ridge'):
        parameter = float(model.split('(')[1][:-1])
        estimator = make_pipeline(StandardScaler(), Ridge(alpha=parameter))
    elif model.startswith('Boosting'):
        parameter = float(model.split('(')[1][:-1])
        estimator = HistGradientBoostingRegressor(l2_regularization=parameter, **POLICY['boosting'])
    else:
        raise ValueError(f'Unknown ML model: {model}')
    estimator.fit(X, y)
    future = list(normalized)
    predictions = []
    for step in range(horizon):
        date = history.index[-1] + pd.Timedelta(days=step + 1)
        value = max(0.0, float(estimator.predict([feature_row(future, date, len(future))])[0]))
        future.append(value)
        predictions.append(value * scale)
    return np.array(predictions)


def predict(history, model, specs, horizon=31):
    values = history.to_numpy()
    if model == 'HW multiplicative' and np.any(values <= 0):
        raise ValueError('Ineligible: requires positive history')
    if np.max(values) == np.min(values):
        return np.repeat(values[-1], horizon)
    if model == 'Naive':
        result = np.repeat(values[-1], horizon)
    elif model == 'Seasonal naive':
        result = np.resize(values[-7:], horizon)
    elif model.startswith('MA('):
        result = moving_average(values, int(model[3:-1]), horizon=horizon)
    elif model in ['SES', 'Holt', 'HW additive', 'HW multiplicative']:
        fit = fit_smoothing(values, model)
        if not fit.mle_retvals.get('success', True):
            raise ValueError('Fit did not converge')
        result = fit.forecast(horizon)
    elif model in ['ARIMA', 'SARIMA']:
        spec = specs[model]
        if spec is None:
            raise ValueError('No converged identification candidate')
        fit = fit_arima(values, *spec)
        if not fit.mle_retvals.get('converged', True):
            raise ValueError('Fit did not converge')
        result = fit.forecast(horizon)
    else:
        result = ml_forecast(history, model, horizon)
    result = np.asarray(result, dtype=float)
    if len(result) != horizon or not np.isfinite(result).all():
        raise ValueError('Invalid forecast')
    return np.maximum(result, 0)


def metrics(frame):
    error = frame.actual - frame.forecast
    scale = frame.scale.replace(0, np.nan)
    return {
        'n': len(frame),
        'MAE': float(error.abs().mean()),
        'RMSE': float(np.sqrt((error**2).mean())),
        'MSE': float((error**2).mean()),
        'Bias': float(error.mean()),
        'MASE': float((error.abs() / scale).mean()),
    }


def choose(validation, allowed=None):
    rows = []
    for model, frame in validation.groupby('model'):
        if len(frame) != 31 or (allowed is not None and model not in allowed):
            continue
        rows.append(dict(model=model, **metrics(frame)))
    candidates = pd.DataFrame(rows)
    return candidates.sort_values(['MSE', 'model']).iloc[0].to_dict()


def evaluate(task):
    group, series = task
    initial = series.loc[:'2023-04-30']
    specs = {}
    identification = []
    for model in ['ARIMA', 'SARIMA']:
        if initial.nunique() == 1:
            specs[model] = None
            continue
        specs[model], records = identify_arima(initial.to_numpy(), model)
        identification.extend(dict(group_id=group, **r) for r in records)
    rows = []
    status = []
    choices = {}
    with threadpool_limits(limits=1):
        for split, origins in [('validation', VALIDATION), ('test', TEST)]:
            for origin in origins:
                history = series.loc[:origin]
                horizon = 31 if split == 'validation' else 30
                actual = series.loc[pd.Timestamp(origin) + pd.Timedelta(days=1) :].iloc[:horizon]
                scale = float(np.mean(np.abs(history.to_numpy()[7:] - history.to_numpy()[:-7])))
                for model in MODELS:
                    caught = []
                    try:
                        with warnings.catch_warnings(record=True) as caught:
                            forecast = predict(history, model, specs, horizon=horizon)
                        for horizon, (date, value) in enumerate(actual.items(), 1):
                            rows.append(
                                dict(
                                    group_id=group,
                                    split=split,
                                    origin=origin,
                                    date=str(date.date()),
                                    horizon=horizon,
                                    model=model,
                                    actual=float(value),
                                    forecast=float(forecast[horizon - 1]),
                                    scale=scale,
                                )
                            )
                        state = 'ok'
                    except (ValueError, np.linalg.LinAlgError) as error:
                        state = str(error)
                    status.append(
                        dict(
                            group_id=group,
                            split=split,
                            origin=origin,
                            model=model,
                            status=state,
                            warnings=' | '.join(str(w.message) for w in caught),
                        )
                    )
            if split == 'validation':
                val = pd.DataFrame(rows)
                choices['all'] = choose(val)
                choices['statistical'] = choose(val, MODELS[:10])
                choices['ml'] = choose(val, MODELS[10:])
        # July forecasts use the frozen May choice. A logged seasonal-naive fallback is explicit.
        selected = choices['all']['model']
        with warnings.catch_warnings(record=True):
            try:
                july = predict(series, selected, specs)
                deployed = selected
            except (ValueError, np.linalg.LinAlgError):
                july = predict(series, 'Seasonal naive', specs)
                deployed = 'Seasonal naive'
    forward = [
        dict(
            group_id=group,
            date=str(date.date()),
            selected_model=selected,
            deployed_model=deployed,
            forecast=value,
        )
        for date, value in zip(pd.date_range('2023-07-01', periods=31), july)
    ]
    selection = [dict(group_id=group, scope=scope, **choice) for scope, choice in choices.items()]
    return rows, status, selection, identification, forward


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    daily, groups = prepare()
    daily.to_csv(OUT / 'hub_daily.csv')
    groups.to_csv(OUT / 'item_groups.csv', index=False)
    inputs = [
        'data/assumptions/bom.csv',
        'data/assumptions/materials.csv',
        'src/monthly_forecasts.py',
        'src/forecast_models.py',
    ]
    manifest = dict(
        POLICY,
        input_hashes={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
        source_sha256=json.loads((ROOT / 'config/experiment.json').read_text())['source_sha256'],
        group_count=groups.group_id.nunique(),
        item_count=len(groups),
    )
    (OUT / 'experiment.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    tasks = [(group, daily[group]) for group in groups.group_id.unique()]
    combined = [[], [], [], [], []]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for i, result in enumerate(pool.map(evaluate, tasks), 1):
            for target, values in zip(combined, result):
                target.extend(values)
            print(f'Completed {i}/{len(tasks)} hub groups', flush=True)
    for name, values in zip(
        ['forecasts', 'fit_status', 'selection', 'identification', 'july_forecasts'], combined
    ):
        pd.DataFrame(values).to_csv(OUT / f'{name}.csv', index=False)
    forecast = pd.DataFrame(combined[0])
    scores = []
    for (group, split, model), frame in forecast.groupby(['group_id', 'split', 'model']):
        scores.append(dict(group_id=group, split=split, model=model, **metrics(frame)))
    scores = pd.DataFrame(scores)
    scores.to_csv(OUT / 'scores.csv', index=False)
    selected = pd.DataFrame(combined[2]).query("scope == 'all'")
    registry = groups.merge(selected[['group_id', 'model', 'MSE', 'MASE']], on='group_id')
    registry = registry.rename(columns={'MSE': 'validation_MSE', 'MASE': 'validation_MASE'})
    registry = registry.merge(
        scores.query("split == 'test'")[['group_id', 'model', 'MAE', 'RMSE', 'MASE', 'n']],
        on=['group_id', 'model'],
        how='left',
    )
    registry['validation_MSE'] *= registry.ratio**2
    registry['MAE'] *= registry.ratio
    registry['RMSE'] *= registry.ratio
    registry.to_csv(OUT / 'item_selection.csv', index=False)
    forward = pd.DataFrame(combined[4]).merge(groups, on='group_id')
    forward.forecast *= forward.ratio
    forward.to_csv(OUT / 'item_july_forecasts.csv', index=False)
    assert len(registry) == 64 and registry.n.eq(30).all(), (
        'Incomplete selected-model test coverage'
    )
    assert len(forward) == 64 * 31
    manifest['complete'] = True
    output_names = [
        'hub_daily',
        'item_groups',
        'forecasts',
        'fit_status',
        'selection',
        'identification',
        'july_forecasts',
        'scores',
        'item_selection',
        'item_july_forecasts',
    ]
    manifest['output_hashes'] = {
        name + '.csv': hashlib.sha256((OUT / (name + '.csv')).read_bytes()).hexdigest()
        for name in output_names
    }
    (OUT / 'experiment.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    print('Hub benchmark complete.', flush=True)


if __name__ == '__main__':
    run()
