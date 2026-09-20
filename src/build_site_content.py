"""Compose one reader from verified weekly and monthly executed notebooks.

This is a presentation build, not a new forecast experiment. The original
notebooks remain runnable companions and all numerical outputs are reused.
"""

import hashlib
import html
import json
import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat

from notebook_html import render
from reader_titles import FORECAST_GROUPS, FORECAST_TITLES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/content/forecasting'


def fragment(cells, index, prefix, temp):
    cells = deepcopy(cells)
    title = f'{index + 1}. {FORECAST_TITLES[index]}'
    cells[0].source = re.sub(r'^## [^\n]+', '## ' + title, cells[0].source, count=1)
    nb = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            'walkthrough': {
                'anchor_prefix': prefix,
                'labels': [FORECAST_TITLES[index]],
                'groups': ({'0': FORECAST_GROUPS[index]} if index in FORECAST_GROUPS else {}),
                'exact_titles': True,
            }
        },
    )
    render(nb, temp)
    text = (Path(temp) / 'notebook.html').read_text(encoding='utf-8')
    body = text.split('<article class="notebook-body">', 1)[1].rsplit('</article>', 1)[0]
    body = body.replace(f'id="{prefix}-section-0"', '')
    return (
        f'<section class="forecast-chapter" id="{prefix}" data-chapter="{index}">{body}</section>'
    )


def demo_html(nb):
    return next(
        o.data['text/html'] for o in nb.cells[7].outputs if 'text/html' in o.get('data', {})
    )


def build():
    sources = {}
    provenance = {}
    for horizon, path, notebook in [
        ('weekly', ROOT / 'results/weekly', ROOT / 'notebooks/02_weekly_forecasting.ipynb'),
        ('monthly', ROOT / 'results/monthly', ROOT / 'notebooks/03_monthly_forecasting.ipynb'),
    ]:
        manifest = json.loads((path / 'experiment.json').read_text())
        assert manifest['complete']
        for name, digest in manifest['input_hashes'].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        for name, digest in manifest['output_hashes'].items():
            assert hashlib.sha256((path / name).read_bytes()).hexdigest() == digest
        sources[horizon] = nbformat.read(notebook, as_version=4)
        provenance[horizon] = hashlib.sha256(notebook.read_bytes()).hexdigest()
    monthly = sources['monthly']
    common = []
    with TemporaryDirectory() as temp:
        scope = deepcopy(monthly.cells[0:2])
        scope[
            0
        ].source = '## Scope\n\nWe forecast daily stock requirements for one central hub supplying all three shops. Weekly forecasts support the next seven days; monthly forecasts cover the next calendar month. Both use the same recorded sales history and BOM.'
        common.append(fragment(scope, 0, 'forecast-section-0', temp))
        methods = deepcopy(monthly.cells[4:6])
        methods[
            0
        ].source = '## Methods\n\nBoth planning horizons compare the same classical and machine learning candidates. Seasonal means a repeating seven-day pattern; forecasting a full month does not imply monthly or annual seasonality.'
        methods[1].outputs = deepcopy(methods[1].outputs)
        for o in methods[1].outputs:
            if 'text/html' in o.get('data', {}):
                o.data['text/html'] = o.data['text/html'].replace(
                    'recursively predict the full month',
                    'recursively predict each future day over the chosen horizon',
                )
        common.append(fragment(methods, 1, 'forecast-section-1', temp))
        demos = {key: demo_html(nb) for key, nb in sources.items()}
        controls = demos['monthly'].split('<div class="method-demo-panel"', 1)[0]
        controls = controls.replace(
            '<label>Demand pattern',
            '<label>Forecast horizon<select class="demo-horizon"><option value="weekly">7 days</option><option value="monthly" selected>31 days</option></select></label><label>Demand pattern',
            1,
        )
        panels = ''
        for horizon, markup in demos.items():
            part = (
                '<div class="method-demo-panel"'
                + markup.split('<div class="method-demo-panel"', 1)[1]
            )
            part = part.rsplit('</div>', 1)[0]
            part = part.replace(
                'class="method-demo-panel"', f'class="method-demo-panel" data-horizon="{horizon}"'
            )
            # Start with only the monthly steady/Naive panel visible.
            if horizon == 'weekly':
                part = re.sub(
                    r'(<div class="method-demo-panel"[^>]*)(?<!hidden)>',
                    lambda m: m[1] + ('' if ' hidden' in m[1] else ' hidden') + '>',
                    part,
                )
            panels += part
        demo_cell = nbformat.v4.new_code_cell(
            '# Teaching visuals reused from the two executed notebooks.',
            metadata={'tags': ['hide-input']},
        )
        demo_cell.outputs = [
            nbformat.v4.new_output('display_data', data={'text/html': controls + panels + '</div>'})
        ]
        common.append(
            fragment(
                [
                    nbformat.v4.new_markdown_cell(
                        '## Explore\n\nChoose a demand pattern, model and forecast horizon. Each method uses the same 84 days of synthetic history; the chart shows the final 28 history days. This teaching example is separate from the real-data results below.'
                    ),
                    demo_cell,
                ],
                2,
                'forecast-section-2',
                temp,
            )
        )
        common.append(fragment(monthly.cells[8:10], 3, 'forecast-section-3', temp))
        variants = []
        for horizon, nb in sources.items():
            chunks = []
            for index, old in [(4, 1), (5, 5), (6, 6), (7, 7), (8, 8)]:
                chunks.append(
                    fragment(
                        nb.cells[old * 2 : old * 2 + 2],
                        index,
                        f'forecast-{horizon}-section-{index}',
                        temp,
                    )
                )
            hidden = ' hidden' if horizon == 'weekly' else ''
            variants.append(
                f'<div class="forecast-variant" id="forecast-{horizon}-results" data-horizon="{horizon}"{hidden}>'
                + ''.join(chunks)
                + '</div>'
            )
    links = ''.join(
        (
            f'<div class="toc-group">{html.escape(FORECAST_GROUPS[i])}</div>'
            if i in FORECAST_GROUPS
            else ''
        )
        + '<a href="#'
        + (f'forecast-section-{i}' if i < 4 else f'forecast-monthly-section-{i}')
        + f'" data-chapter="{i}" data-nb-target="'
        + (f'forecast-section-{i}' if i < 4 else f'forecast-monthly-section-{i}')
        + '">'
        + html.escape(f'{i + 1}. {title}')
        + '</a>'
        for i, title in enumerate(FORECAST_TITLES)
    )
    toc = (
        '<aside class="notebook-toc" aria-label="Forecasting sections"><button class="toc-toggle" aria-expanded="false">Chapters <span aria-hidden="true">⌄</span></button><div class="toc-links">'
        + links
        + '</div></aside>'
    )
    switch = '<div class="forecast-switchbar"><span class="forecast-switch-label">Forecast horizon</span><div class="horizon-buttons" role="group" aria-label="Results forecast horizon"><button type="button" data-forecast-horizon="weekly" aria-pressed="false" aria-controls="forecast-weekly-results"><strong>Weekly</strong><span>(7 days)</span></button><button type="button" data-forecast-horizon="monthly" aria-pressed="true" aria-controls="forecast-monthly-results"><strong>Monthly</strong><span>(Full month)</span></button></div></div>'
    result = (
        toc
        + '<article class="notebook-body">'
        + ''.join(common)
        + '<div class="forecast-results-region">'
        + switch
        + ''.join(variants)
        + '</div></article>'
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'notebook.html').write_text(result, encoding='utf-8')
    (OUT / 'reader_manifest.json').write_text(
        json.dumps(
            {
                'source_notebook_hashes': provenance,
                'titles': FORECAST_TITLES,
                'default_horizon': 'monthly',
            },
            indent=2,
        ),
        encoding='utf-8',
    )
    print('Combined forecasting reader built; numerical results unchanged.')


if __name__ == '__main__':
    build()
