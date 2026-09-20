"""Calendar-month teaching view using the shared explorer renderer."""

from forecast_method_demo import build_demo as build_shared_demo
from monthly_forecasts import predict


def build_demo():
    return build_shared_demo(horizon=31, predict_fn=predict)
