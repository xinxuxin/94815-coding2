"""Pure-Python market data fetching and feature engineering."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from .schemas import MarketDataContext, MarketDataSummary


DEFAULT_PERIOD = "1y"
DEFAULT_INTERVAL = "1d"
MIN_REQUIRED_CLOSE_ROWS = 2
REQUIRED_COLUMNS = ("Close",)


def fetch_price_history(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """Fetch daily OHLCV history for a single ticker using yfinance.

    Raises:
        ValueError: If the returned dataset is empty or lacks closing prices.
    """

    history = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    history = _normalize_history_frame(history)

    if history.empty:
        raise ValueError(f"No price history returned for ticker '{ticker}'.")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in history.columns]
    if missing_columns:
        raise ValueError(
            f"Price history for ticker '{ticker}' is missing required columns: {missing_columns}."
        )

    history = history.sort_index()
    history = history.loc[history["Close"].notna()].copy()
    if history.empty or len(history) < MIN_REQUIRED_CLOSE_ROWS:
        raise ValueError(f"Ticker '{ticker}' does not have enough non-null closing prices.")

    if "Volume" not in history.columns:
        history["Volume"] = 0.0
    else:
        history["Volume"] = history["Volume"].fillna(0.0)

    return history


def compute_common_features(df: pd.DataFrame) -> dict[str, Any]:
    """Compute market features shared by both strategies."""

    clean = _prepare_history(df)
    close = clean["Close"]
    volume = clean["Volume"]
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan)

    ma20 = _tail_mean(close, 20)
    ma50 = _tail_mean(close, 50)
    price_30d_ago = _lookback_close(close, 30)
    pct_change_30d = _pct_change(close.iloc[-1], price_30d_ago)
    daily_return_mean_30d = _safe_number(returns.tail(30).mean() * 100.0)
    volatility_30d = _safe_number(returns.tail(30).std(ddof=0))
    max_single_day_drop_90d = _safe_number(
        min(returns.tail(90).min(skipna=True) * 100.0, 0.0)
        if not returns.tail(90).dropna().empty
        else 0.0
    )

    return {
        "history_rows": int(len(clean)),
        "has_full_30d_window": len(clean) >= 31,
        "has_full_90d_window": len(clean) >= 91,
        "has_full_1y_window": len(clean) >= 252,
        "current_price": _round_price(close.iloc[-1]),
        "price_30d_ago": _round_price(price_30d_ago),
        "pct_change_30d": _round_metric(pct_change_30d),
        "avg_daily_volume_30d": float(int(round(_safe_number(volume.tail(30).mean())))),
        "volatility_30d": _round_metric(volatility_30d),
        "moving_avg_20d": _round_price(ma20),
        "moving_avg_50d": _round_price(ma50),
        "daily_return_mean_30d": _round_metric(daily_return_mean_30d),
        "max_single_day_drop_90d": _round_metric(max_single_day_drop_90d),
    }


def compute_momentum_features(df: pd.DataFrame) -> dict[str, Any]:
    """Compute features used by the Momentum Trader strategy."""

    clean = _prepare_history(df)
    close = clean["Close"]
    volume = clean["Volume"]

    current_price = _safe_number(close.iloc[-1])
    ma20 = _tail_mean(close, 20)
    ma50 = _tail_mean(close, 50)
    avg_volume_30d = _safe_number(volume.tail(30).mean())
    current_volume = _safe_number(volume.iloc[-1])

    return_30d = _pct_change(current_price, _lookback_close(close, 30))
    return_90d = _pct_change(current_price, _lookback_close(close, 90))
    volume_vs_30d_avg = current_volume / avg_volume_30d if avg_volume_30d > 0 else 0.0

    return {
        "price_above_ma20": bool(current_price >= ma20) if ma20 > 0 else False,
        "ma20_above_ma50": bool(ma20 >= ma50) if ma50 > 0 else False,
        "volume_vs_30d_avg": _round_metric(volume_vs_30d_avg),
        "return_30d": _round_metric(return_30d),
        "return_90d": _round_metric(return_90d),
    }


def compute_value_contrarian_features(df: pd.DataFrame) -> dict[str, Any]:
    """Compute features used by the Value Contrarian strategy."""

    clean = _prepare_history(df)
    close = clean["Close"]
    trailing_year = close.tail(252)
    trailing_ninety = close.tail(90)

    current_price = _safe_number(close.iloc[-1])
    high_52w = _safe_number(trailing_year.max())
    low_52w = _safe_number(trailing_year.min())
    recent_peak = _safe_number(trailing_ninety.max())

    distance_from_52w_high_pct = (
        ((high_52w - current_price) / high_52w) * 100.0 if high_52w > 0 else 0.0
    )
    distance_from_52w_low_pct = (
        ((current_price - low_52w) / low_52w) * 100.0 if low_52w > 0 else 0.0
    )
    recent_drawdown_pct = (
        ((recent_peak - current_price) / recent_peak) * 100.0 if recent_peak > 0 else 0.0
    )
    rsi_14 = _compute_rsi(close, window=14)
    return_30d = _pct_change(current_price, _lookback_close(close, 30))
    surge_or_drop_signal = _classify_recent_move(
        return_30d=return_30d,
        recent_drawdown_pct=recent_drawdown_pct,
        rsi_14=rsi_14,
    )

    return {
        "distance_from_52w_high_pct": _round_metric(distance_from_52w_high_pct),
        "distance_from_52w_low_pct": _round_metric(distance_from_52w_low_pct),
        "recent_drawdown_pct": _round_metric(recent_drawdown_pct),
        "RSI_14": _round_metric(rsi_14),
        "surge_or_drop_signal": surge_or_drop_signal,
    }


def build_market_data_context(ticker: str) -> dict[str, Any]:
    """Build the compact market context that later strategy agents will consume."""

    history = fetch_price_history(ticker=ticker, period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL)
    summary_dict = {
        **compute_common_features(history),
        **compute_momentum_features(history),
        **compute_value_contrarian_features(history),
    }
    summary = MarketDataSummary.model_validate(summary_dict)
    context = MarketDataContext(
        ticker=ticker.upper(),
        run_date=date.today().isoformat(),
        market_data_summary=summary,
    )
    return context.model_dump()


def _normalize_history_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance output into a single-index frame."""

    if isinstance(df.columns, pd.MultiIndex):
        flattened = []
        for column in df.columns.to_flat_index():
            flattened.append(str(column[-1] if column[-1] else column[0]))
        df = df.copy()
        df.columns = flattened

    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df = df.tz_localize(None)

    return df


def _prepare_history(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and sanitize a history frame for indicator calculations."""

    if df.empty:
        raise ValueError("Price history is empty.")
    if "Close" not in df.columns:
        raise ValueError("Price history must include a 'Close' column.")

    clean = df.copy()
    clean["Close"] = pd.to_numeric(clean["Close"], errors="coerce")
    clean = clean.loc[clean["Close"].notna()].copy()
    if clean.empty or len(clean) < MIN_REQUIRED_CLOSE_ROWS:
        raise ValueError("Price history must contain at least two non-null close values.")

    if "Volume" not in clean.columns:
        clean["Volume"] = 0.0
    clean["Volume"] = pd.to_numeric(clean["Volume"], errors="coerce").fillna(0.0)

    return clean.sort_index()


def _tail_mean(series: pd.Series, window: int) -> float:
    """Return the trailing mean, falling back to the available history."""

    tail = series.tail(window)
    return _safe_number(tail.mean())


def _lookback_close(series: pd.Series, trading_days_back: int) -> float:
    """Return the close from N trading days back, or the earliest available."""

    if len(series) <= trading_days_back:
        return _safe_number(series.iloc[0])
    return _safe_number(series.iloc[-(trading_days_back + 1)])


def _pct_change(current_value: float, base_value: float) -> float:
    """Return percentage change, guarding against divide-by-zero and NaN values."""

    current_value = _safe_number(current_value)
    base_value = _safe_number(base_value)
    if base_value <= 0:
        return 0.0
    return ((current_value - base_value) / base_value) * 100.0


def _compute_rsi(close: pd.Series, window: int = 14) -> float:
    """Compute a robust latest RSI value from a closing-price series."""

    if len(close) < 2:
        return 50.0

    delta = close.diff().dropna()
    if delta.empty:
        return 50.0

    tail = delta.tail(min(window, len(delta)))
    gains = tail.clip(lower=0.0)
    losses = -tail.clip(upper=0.0)

    avg_gain = _safe_number(gains.mean())
    avg_loss = _safe_number(losses.mean())

    if avg_gain == 0.0 and avg_loss == 0.0:
        return 50.0
    if avg_loss == 0.0:
        return 100.0
    if avg_gain == 0.0:
        return 0.0

    relative_strength = avg_gain / avg_loss
    return _safe_number(100.0 - (100.0 / (1.0 + relative_strength)))


def _classify_recent_move(
    return_30d: float,
    recent_drawdown_pct: float,
    rsi_14: float,
) -> str:
    """Convert recent move metrics into a compact contrarian signal."""

    if return_30d >= 12.0 or (return_30d >= 8.0 and rsi_14 >= 70.0):
        return "surge"
    if return_30d <= -10.0 or recent_drawdown_pct >= 15.0 or (return_30d < 0 and rsi_14 <= 35.0):
        return "drop"
    return "neutral"


def _safe_number(value: Any, default: float = 0.0) -> float:
    """Convert scalars to a finite float with a deterministic fallback."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(numeric) or np.isinf(numeric):
        return default
    return numeric


def _round_price(value: Any) -> float:
    """Round price-like values for compact LLM-friendly context."""

    return round(_safe_number(value), 4)


def _round_metric(value: Any) -> float:
    """Round derived metrics for compact LLM-friendly context."""

    return round(_safe_number(value), 4)
