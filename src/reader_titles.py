"""One source for concise, identical navigation and chapter titles."""

import re

FORECAST_TITLES = [
    'Forecasting scope',
    'Forecasting methods',
    'Explore the methods',
    'Forecast measures',
    'Validation and testing',
    'May model selection',
    'June model evaluation',
    'Errors by stock type',
    'July requirements',
]
FORECAST_GROUPS = {
    0: 'Set up forecasts',
    1: 'Choose and compare methods',
    4: 'Read the results',
    8: 'Use the forecasts',
}
EDA_TITLES = [
    'Business and records',
    'Consistent labels',
    'Missing and duplicate rows',
    'Unusual values',
    'Daily sales records',
    'Sales by shop',
    'Business growth',
    'Revenue drivers',
    'Daily variation',
    'Weekly patterns',
    'Hourly patterns',
    'Sales by category',
    'Sales by product',
    'Sales to stock requirements',
    'Forecasting handoff',
]


def apply_eda_titles(nb):
    index = 0
    for cell in nb.cells:
        if cell.cell_type == 'markdown' and cell.source.startswith('## '):
            title = f'{index + 1}. {EDA_TITLES[index]}'
            cell.source = re.sub(r'^## [^\n]+', '## ' + title, cell.source, count=1)
            index += 1
    assert index == len(EDA_TITLES)
    nb.metadata.walkthrough.labels = EDA_TITLES
    nb.metadata.walkthrough.exact_titles = True
    nb.metadata.walkthrough.groups = {
        '0': 'Data preparation',
        '5': 'Business performance',
        '8': 'Sales patterns',
        '11': 'Product mix',
        '13': 'Hub requirements',
    }
    return nb
