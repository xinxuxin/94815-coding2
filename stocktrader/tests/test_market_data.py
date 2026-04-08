"""Tests for pure-Python market-data calculations."""

from __future__ import annotations

import pandas as pd
from typing import Optional

from src.market_data import (
    build_market_data_context,
    compute_common_features,
    compute_momentum_features,
    compute_value_contrarian_features,
)
from src.schemas import MarketDataContext, MarketDataSummary


def _make_history(
    close_values: list[float],
    volume_values: Optional[list[float]] = None,
) -> pd.DataFrame:
    """Create a synthetic daily price frame for indicator tests."""

    if volume_values is None:
        volume_values = [1_000_000.0] * len(close_values)

    index = pd.date_range("2024-01-01", periods=len(close_values), freq="B")
    return pd.DataFrame({"Close": close_values, "Volume": volume_values}, index=index)


def test_indicator_calculations_on_rising_series() -> None:
    """Momentum-friendly series should produce positive trend indicators."""

    df = _make_history(list(range(100, 230)), [1_000_000 + (i * 5_000) for i in range(130)])

    common = compute_common_features(df)
    momentum = compute_momentum_features(df)
    value = compute_value_contrarian_features(df)

    assert common["history_rows"] == 130
    assert common["current_price"] == 229.0
    assert common["pct_change_30d"] > 0
    assert common["moving_avg_20d"] > common["moving_avg_50d"]
    assert common["max_single_day_drop_90d"] == 0.0

    assert momentum["price_above_ma20"] is True
    assert momentum["ma20_above_ma50"] is True
    assert momentum["return_30d"] > 0
    assert momentum["return_90d"] > momentum["return_30d"]

    assert value["distance_from_52w_high_pct"] == 0.0
    assert value["distance_from_52w_low_pct"] > 0
    assert value["RSI_14"] > 70.0
    assert value["surge_or_drop_signal"] == "surge"


def test_rsi_behavior_for_up_down_and_flat_series() -> None:
    """RSI should trend high on gains, low on losses, and neutral on flat prices."""

    up_df = _make_history(list(range(100, 130)))
    down_df = _make_history(list(range(130, 100, -1)))
    flat_df = _make_history([100.0] * 30)

    up_rsi = compute_value_contrarian_features(up_df)["RSI_14"]
    down_rsi = compute_value_contrarian_features(down_df)["RSI_14"]
    flat_rsi = compute_value_contrarian_features(flat_df)["RSI_14"]

    assert up_rsi > 70.0
    assert down_rsi < 30.0
    assert flat_rsi == 50.0


def test_schema_validation_for_market_data_context(monkeypatch) -> None:
    """Combined market context should validate cleanly against the Pydantic schema."""

    df = _make_history(list(range(80, 200)))

    monkeypatch.setattr("src.market_data.fetch_price_history", lambda ticker, period="1y", interval="1d": df)

    context = build_market_data_context("MSFT")
    validated = MarketDataContext.model_validate(context)

    assert validated.ticker == "MSFT"
    assert isinstance(validated.market_data_summary, MarketDataSummary)
    assert validated.market_data_summary.history_rows == 120
    assert validated.market_data_summary.current_price == 199.0


def test_short_history_is_handled_without_nan_leaks() -> None:
    """Newly listed or short-history names should still produce clean numeric output."""

    df = _make_history([10, 11, 12, 13, 14, 15, 16, 17, 18, 19], [100] * 10)

    summary = {
        **compute_common_features(df),
        **compute_momentum_features(df),
        **compute_value_contrarian_features(df),
    }

    validated = MarketDataSummary.model_validate(summary)

    assert validated.has_full_30d_window is False
    assert validated.has_full_90d_window is False
    assert validated.current_price == 19.0
    assert validated.RSI_14 >= 0.0
