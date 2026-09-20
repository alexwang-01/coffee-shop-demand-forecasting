# Data source and project assumptions

## Observed source data

`raw/Coffee Shop Sales.xlsx` is the **Coffee Shop Sales** sample dataset from
[Maven Analytics](https://mavenanalytics.io/data-playground/coffee-shop-sales). Maven describes it
as transaction records for a fictitious coffee shop operating at three New York City locations and
lists the dataset license as **Public Domain**.

The workbook included here contains 149,116 transaction rows from 1 January to 30 June 2023. Its
SHA-256 hash is:

```text
287d06d19f7a832d48f1deea7b149836fb32d591010f060bdcf8d1959653bfe1
```

The workbook is kept unchanged so the analysis can verify the source hash before processing it.

## Project-defined data

The files under `assumptions/` are analytical definitions created for this project:

- `product_mapping.csv` classifies the source catalogue.
- `bom.csv` maps each product sale to ingredients, packaging or a ready-to-sell stock item.
- `materials.csv` describes those stock items and their units.
- `assumptions.json` states the boundary between observed data and the hypothetical planning setting.

The Singapore setting, Store A/B/C labels, central hub and BOM are not supplied by Maven Analytics.
They provide a coherent scenario for translating product transactions into stock-item demand. This
release forecasts requirements only; it does not claim observed inventory, supplier or distribution
performance.

