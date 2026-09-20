# Validation and limitations

## Controls built into the workflow

- The raw workbook hash is checked before transformation.
- BOM keys, positive quantities, material coverage and source product coverage are asserted.
- Forecasts use only observations available at each origin.
- A model must cover every May validation date before it can be selected.
- May selects the model; June only evaluates the frozen choice.
- Selected-group results reconcile to all 64 stock-item outputs.
- Result manifests record input and output hashes.
- Automated tests cover causal features, exact selection, monthly coverage, proportional grouping,
  deterministic machine-learning output and manifest reconciliation.

## Interpretation limits

This is a retrospective forecasting study. June results had been inspected during project development,
so they should be read as a transparent holdout comparison rather than a claim of untouched production
performance. July requirements are forward forecasts because the source data end on 30 June; no July
actuals are available for scoring.

The Singapore geography, Store A/B/C labels, central hub and BOM are project assumptions. The source
transactions come from three fictitious New York City stores. No inventory position, purchase orders,
lead times, supplier constraints, costs, waste or fill-rate data are present. Consequently, the July
figures are forecast requirements rather than order recommendations.

Aggregate results can hide individual failures. The interface therefore shows category-level error
comparisons and a complete group table. The monthly experiment has a longer horizon and fewer forecast
origins than the weekly experiment, so its uncertainty and model risk are higher.

