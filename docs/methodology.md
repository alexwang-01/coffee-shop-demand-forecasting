# Forecasting methodology

## Analytical grain

The source records product transactions at three stores. A project-defined bill of materials converts
each product sale into stock-item requirements. Requirements are added across the three relabelled
stores to represent one hypothetical central hub.

The 64 stock items reduce to 61 independent forecasting groups because three pairs of items have
exactly proportional demand under the BOM. Each group is modelled once; proportional items recover
their own quantities by applying the verified ratio.

## Candidate methods

Every eligible group compares the same 16 candidates:

- Classical: naive, seasonal naive, 7- and 14-day moving averages, simple exponential smoothing,
  Holt, additive and multiplicative Holt-Winters, ARIMA and SARIMA.
- Machine learning: linear regression, Ridge with two penalties, random forest and histogram gradient
  boosting with two regularisation settings.

The machine-learning features use lags 1, 2, 3, 7 and 14; trailing 7- and 14-day means; trailing
7-day standard deviation; a linear time index; and weekday sine/cosine terms. Multi-step forecasts
are recursive, so later days use earlier predictions when the actual value is unavailable.

ARIMA and SARIMA orders are identified with a bounded AIC search using January-April history and are
then frozen. Other model parameters are refitted using only the history available at each forecast
origin.

## Selection and evaluation

Model selection happens independently for each of the 61 groups. A candidate must produce every May
validation forecast to be eligible. The candidate with the lowest May mean squared error (MSE) wins;
there is no 1% tolerance or subjective simplicity preference. Alphabetical order resolves exact
numeric ties only.

Two horizons answer different planning questions:

| Experiment | May selection period | June evaluation period | Forward output |
|---|---:|---:|---:|
| Weekly | Four separate 7-day windows, 28 days total | Four separate 7-day windows, 28 days total | 1-7 July |
| Monthly | Full 31-day calendar month | Full available June, 30 days | 1-31 July |

The selected method is frozen after May. June evaluates that choice against unseen dates; June does
not replace a weak selected model. The method is refitted with the history available at each June
origin, which separates choosing a method from updating its fitted state.

## Measures

- **MSE** selects a model within a group and gives larger daily misses more weight.
- **MAE** expresses a typical absolute miss in the stock item's own unit.
- **RMSE** expresses the square-root MSE in the original unit.
- **Bias** is actual requirement minus forecast; positive values indicate underforecasting.
- **MASE** divides absolute error by the group's historical seven-day naive scale, allowing groups
  with different units and volumes to be averaged.

The displayed baseline is seasonal naive: repeat the demand observed seven days earlier. It is both a
candidate and the common June comparison. A baseline MASE of 1.37 and a selected-model MASE of 1.00
mean the selected models have about `(1.37 - 1.00) / 1.37` less average scaled error. MASE values are
error scores, not percentages of demand.

