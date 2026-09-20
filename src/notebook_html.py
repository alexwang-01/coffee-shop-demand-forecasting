"""Render all executed notebook cells without rerunning the analysis."""

import html
import json
import re
from pathlib import Path
from xml.etree import ElementTree

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / 'build/notebook'


def markdown(text):
    """Small renderer for this notebook's deliberate headings and prose only."""
    parts = []
    for block in text.split('\n\n'):
        for piece in re.split(r'(?m)(?=^#{1,3} )', block):
            if not piece.strip():
                continue
            lines = piece.splitlines()
            if lines[0].startswith('#'):
                level = len(lines[0].split(' ')[0])
                parts.append(f'<h{level}>' + html.escape(lines[0][level + 1 :]) + f'</h{level}>')
                if len(lines) > 1:
                    parts.append('<p>' + html.escape('\n'.join(lines[1:])) + '</p>')
            else:
                parts.append('<p>' + html.escape(piece) + '</p>')
    return ''.join(parts)


TOC_LABELS = [
    'Question & scope',
    'Environment & source',
    'Inspect transactions',
    'Data quality checks',
    'Daily sales & coverage',
    'Sales by category & store',
    'Weekday & zero-sale patterns',
    'Sales frequency groups',
    'Time-based validation',
    'Baseline & statistical models',
    'Features & recursive ML',
    'Croston-SBA method',
    'Evaluation metrics',
    'Validation & model selection',
    'June forecast evaluation',
    'Results by segment',
    'Weekly forecast stability',
    'Individual forecast errors',
    'Matched V1 comparison',
    'Forecasts to materials',
    'Planning handoff',
    'Operating scenarios',
    'Checks & interpretation',
    'Conclusions & limitations',
]


def flatten_table_headers(fragment):
    """Combine pandas column/index header rows without changing body cells."""

    def combine(match):
        header = ElementTree.fromstring(match.group(0))
        rows = header.findall('tr')
        if len(rows) < 2:
            return match.group(0)
        grid = {}
        for row_index, row in enumerate(rows):
            column = 0
            for cell in row:
                while (row_index, column) in grid:
                    column += 1
                label = ''.join(cell.itertext()).strip()
                width = int(cell.get('colspan', '1'))
                height = int(cell.get('rowspan', '1'))
                for y in range(row_index, row_index + height):
                    for x in range(column, column + width):
                        grid[y, x] = label
                column += width
        headings = []
        for column in range(max(x for _, x in grid) + 1):
            labels = list(dict.fromkeys(grid.get((row, column), '') for row in range(len(rows))))
            title = ' / '.join(label for label in labels if label)
            headings.append('<th scope="col">' + html.escape(title) + '</th>')
        return '<thead><tr>' + ''.join(headings) + '</tr></thead>'

    return re.sub(r'<thead\b[^>]*>.*?</thead>', combine, fragment, flags=re.S)


def render(nb, output_dir=None):
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    sections = []
    toc = []
    section = -1
    anchor_prefix = nb.metadata.get('walkthrough', {}).get('anchor_prefix', 'nb')
    groups = {
        0: 'Data preparation',
        5: 'Exploratory data analysis',
        8: 'Forecasting methodology',
        13: 'Model evaluation and results',
        19: 'Forecast handoff',
        23: 'Conclusions and limitations',
    }
    if 'walkthrough' in nb.metadata:
        groups = {int(k): v for k, v in nb.metadata.walkthrough.groups.items()}
    labels = nb.metadata.get('walkthrough', {}).get('labels', TOC_LABELS)
    group_figures = nb.metadata.get('walkthrough', {}).get('group_figures', {})
    moved_figures = {}
    for group, cell_index in group_figures.items():
        output_index = next(
            i
            for i, output in enumerate(nb.cells[cell_index].outputs)
            if 'image/png' in output.get('data', {})
        )
        moved_figures[(cell_index, output_index)] = int(group)
    for cell_index, cell in enumerate(nb.cells):
        if cell.cell_type == 'markdown':
            for part in re.split(r'(?m)(?=^## )', cell.source):
                if not part.strip():
                    continue
                match = re.search(r'^## (.+)', part, re.M)
                if match:
                    section += 1
                    if section in groups:
                        title = groups[section]
                        toc.append(('group', title))
                        sections.append(f'<h1 class="notebook-part">{html.escape(title)}</h1>')
                    for (source_cell, source_output), group in moved_figures.items():
                        if group == section:
                            png = nb.cells[source_cell].outputs[source_output].data['image/png']
                            sections.append(
                                '<div class="nb-output"><img class="nb-figure" alt="Forecasting workflow" src="data:image/png;base64,'
                                + png
                                + '"></div>'
                            )
                    toc.append(
                        (
                            f'{anchor_prefix}-section-{section}',
                            match.group(1)
                            if nb.metadata.get('walkthrough', {}).get('exact_titles')
                            else f'{section + 1}. {labels[section]}',
                        )
                    )
                anchor = f' id="{anchor_prefix}-section-{section}"' if match else ''
                sections.append(f'<div class="nb-markdown"{anchor}>' + markdown(part) + '</div>')
        elif cell.cell_type == 'code':
            is_model_fit = (
                cell.source.lstrip().startswith(('validation,', 'test,'))
                and 'evaluate(' in cell.source
            )

            def is_execution_log(output):
                return output.output_type == 'stream' and (
                    output.get('name') == 'stderr'
                    or is_model_fit
                    or cell.metadata.get('fold_streams', False)
                )

            for output_index, output in enumerate(cell.get('outputs', [])):
                if (cell_index, output_index) in moved_figures:
                    continue
                if is_execution_log(output):
                    continue
                data = output.get('data', {})
                if 'image/png' in data:
                    content = (
                        '<img class="nb-figure" alt="Executed notebook figure" src="data:image/png;base64,'
                        + data['image/png']
                        + '">'
                    )
                elif 'text/html' in data:
                    content = flatten_table_headers(data['text/html'])
                elif 'text/plain' in data:
                    content = '<pre>' + html.escape(data['text/plain']) + '</pre>'
                elif output.output_type == 'stream':
                    content = '<pre>' + html.escape(output.text) + '</pre>'
                elif output.output_type == 'error':
                    raise RuntimeError(output.evalue)
                else:
                    continue
                sections.append(
                    '<div class="nb-output"><div class="cell-prompt">Out:</div><div class="cell-body">'
                    + content
                    + '</div></div>'
                )
    (output_dir / 'notebook.html').write_text(
        '<aside class="notebook-toc" aria-label="Analysis sections">'
        + ''.join(
            (
                f'<h2 class="toc-group">{html.escape(title)}</h2>'
                if id == 'group'
                else f'<a href="#{id}" data-nb-target="{id}">{html.escape(title)}</a>'
            )
            for id, title in toc
        )
        + '</aside><article class="notebook-body">'
        + ''.join(sections)
        + '</article>',
        encoding='utf8',
    )
    (output_dir / 'notebook_render_manifest.json').write_text(
        json.dumps(
            {
                'cells': len(nb.cells),
                'code_cells': sum(c.cell_type == 'code' for c in nb.cells),
                'sections': sum(id != 'group' for id, title in toc),
                'all_cells_rendered': True,
                'code_inputs_included': False,
            },
            indent=2,
        )
    )
