"""Independently reconcile saved forecasts; never refit or modify benchmark outputs."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from forecast_models import stable_sha256

ROOT = Path(__file__).resolve().parents[1]


def raw_requirements():
    config = json.loads((ROOT / 'config/experiment.json').read_text())
    source = (ROOT / config['source']).resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config['source_sha256']
    sales = pd.read_excel(source)
    bom = pd.read_csv(ROOT / 'data/assumptions/bom.csv')
    # Long-form multiplication deliberately differs from the engine's matrix product.
    sales['date'] = pd.to_datetime(sales.transaction_date).dt.normalize()
    sold = sales.groupby(['date', 'product_id'], as_index=False).transaction_qty.sum()
    joined = sold.merge(bom, on='product_id', validate='many_to_many')
    joined['requirement'] = joined.transaction_qty * joined.quantity_per_sale
    return joined.groupby(['date', 'material_id']).requirement.sum().unstack(fill_value=0)


def audit(folder, validation_days, test_days, july_days, raw):
    path = ROOT / folder
    manifest = json.loads((path / 'experiment.json').read_text())
    for relative, digest in manifest['input_hashes'].items():
        assert stable_sha256(ROOT / relative) == digest, relative
    for relative, digest in manifest['output_hashes'].items():
        assert stable_sha256(path / relative) == digest, relative
    frame = pd.read_csv(path / 'forecasts.csv')
    selection = pd.read_csv(path / 'selection.csv').query("scope == 'all'")
    daily = pd.read_csv(path / 'hub_daily.csv', index_col=0, parse_dates=True)
    np.testing.assert_allclose(daily, raw.reindex(index=daily.index, columns=daily.columns))
    assert not frame.duplicated(['group_id', 'split', 'origin', 'date', 'model']).any()
    assert np.isfinite(frame[['actual', 'forecast', 'scale']]).all().all()
    assert frame.scale.gt(0).all() and frame.forecast.ge(0).all()
    for (group, origin), rows in frame.groupby(['group_id', 'origin']):
        history = daily.loc[:origin, group].values
        np.testing.assert_allclose(rows.scale, np.mean(abs(history[7:] - history[:-7])))
        assert (pd.to_datetime(rows.date) > pd.Timestamp(origin)).all()
        np.testing.assert_allclose(rows.actual, daily.loc[pd.to_datetime(rows.date), group])
        for model in ['Naive', 'Seasonal naive']:
            forecasts = rows[rows.model.eq(model)]
            expected = (
                np.repeat(history[-1], len(forecasts))
                if model == 'Naive'
                else np.resize(history[-7:], len(forecasts))
            )
            np.testing.assert_allclose(forecasts.forecast, expected)
    frame['error'] = frame.actual - frame.forecast
    frame['absolute'] = frame.error.abs()
    frame['squared'] = frame.error**2
    frame['scaled'] = frame.absolute / frame.scale
    metrics = (
        frame.groupby(['group_id', 'split', 'model'])
        .agg(
            n=('error', 'size'),
            MSE=('squared', 'mean'),
            MAE=('absolute', 'mean'),
            Bias=('error', 'mean'),
            MASE=('scaled', 'mean'),
        )
        .reset_index()
    )
    metrics['RMSE'] = np.sqrt(metrics.MSE)
    saved = pd.read_csv(path / 'scores.csv')
    merged = metrics.merge(saved, on=['group_id', 'split', 'model'], suffixes=('_a', '_b'))
    assert len(merged) == len(metrics) == len(saved)
    for metric in ['n', 'MSE', 'MAE', 'Bias', 'MASE', 'RMSE']:
        np.testing.assert_allclose(merged[metric + '_a'], merged[metric + '_b'])
    eligible = metrics[metrics.split.eq('validation') & metrics.n.eq(validation_days)]
    winners = eligible.sort_values(['group_id', 'MSE', 'model']).drop_duplicates('group_id')
    merged = winners.merge(selection, on='group_id', suffixes=('_a', '_b'))
    assert len(merged) == 61 and merged.model_a.eq(merged.model_b).all()
    selected = metrics[metrics.split.eq('test')].merge(selection[['group_id', 'model']])
    assert len(selected) == 61 and selected.n.eq(test_days).all()
    baseline = metrics[metrics.split.eq('test') & metrics.model.eq('Seasonal naive')]
    comparison = selected.merge(baseline, on='group_id', suffixes=('_s', '_b'))
    groups = pd.read_csv(path / 'item_groups.csv')
    july = pd.read_csv(path / 'july_forecasts.csv')
    items = pd.read_csv(path / 'item_july_forecasts.csv')
    assert len(july) == 61 * july_days and len(items) == 64 * july_days
    assert not july.duplicated(['group_id', 'date']).any()
    assert not items.duplicated(['material_id', 'date']).any()
    expected_dates = set(pd.date_range('2023-07-01', periods=july_days).strftime('%Y-%m-%d'))
    assert set(july.date) == expected_dates
    assert july.selected_model.eq(july.deployed_model).all()
    merged = july.merge(selection[['group_id', 'model']], on='group_id')
    assert merged.selected_model.eq(merged.model).all()
    merged = items.merge(
        july[['group_id', 'date', 'forecast']], on=['group_id', 'date'], suffixes=('_i', '_g')
    )
    np.testing.assert_allclose(merged.forecast_i, merged.forecast_g * merged.ratio)
    for row in groups.itertuples():
        np.testing.assert_allclose(daily[row.material_id], daily[row.group_id] * row.ratio)
    displayed = pd.read_csv(path / 'group_selection.csv').merge(winners, on='group_id')
    np.testing.assert_allclose(displayed['May MSE'], displayed.MSE)
    eligible_counts = eligible.groupby('group_id').size()
    np.testing.assert_array_equal(
        displayed['Eligible candidates'], displayed.group_id.map(eligible_counts)
    )
    displayed = pd.read_csv(path / 'group_test_results.csv').merge(comparison, on='group_id')
    for metric in ['MAE', 'RMSE', 'Bias', 'MASE']:
        np.testing.assert_allclose(displayed['June ' + metric], displayed[metric + '_s'])
    np.testing.assert_allclose(displayed['Baseline MASE'], displayed.MASE_b)
    totals_file = 'weekly_requirements.csv' if july_days == 7 else 'monthly_requirements.csv'
    totals = pd.read_csv(path / totals_file).set_index('material_id')
    np.testing.assert_allclose(
        totals.forecast, items.groupby('material_id').forecast.sum().reindex(totals.index)
    )
    return {
        'status': 'pass',
        'forecast_rows': len(frame),
        'groups': 61,
        'items': 64,
        'july_days': july_days,
        'selected_models': selection.model.value_counts().to_dict(),
        'june_mean_MASE': float(selected.MASE.mean()),
        'baseline_mean_MASE': float(baseline.MASE.mean()),
        'groups_worse_than_baseline': int((comparison.MASE_s > comparison.MASE_b).sum()),
        'checks': [
            'source and output hashes',
            'raw sales/BOM reconciliation',
            'forecast dates, actuals and historical MASE scales',
            'both naive formulas',
            'all saved metrics',
            'minimum May MSE selection and eligibility',
            'June displayed metrics',
            'July dates, model choices, BOM ratios and totals',
        ],
    }


if __name__ == '__main__':
    raw = raw_requirements()
    report = {
        name: audit(folder, vd, td, jd, raw)
        for name, folder, vd, td, jd in [
            ('weekly', 'results/weekly', 28, 28, 7),
            ('monthly', 'results/monthly', 31, 30, 31),
        ]
    }
    target = ROOT / 'results/forecast_audit.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))
