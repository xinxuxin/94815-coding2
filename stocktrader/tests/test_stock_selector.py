"""Tests for data-driven stock classification and selection."""

from __future__ import annotations

from src.stock_selector import classify_stock_condition, select_representative_stocks


def _context(
    ticker: str,
    *,
    volatility_30d: float,
    return_30d: float,
    return_90d: float,
    price_vs_ma20_pct: float,
    ma20_vs_ma50_pct: float,
    recent_drawdown_pct: float,
    distance_from_52w_high_pct: float,
    distance_from_52w_low_pct: float,
    volume_vs_30d_avg: float,
    rsi_14: float,
    surge_or_drop_signal: str,
) -> dict:
    """Build a minimal valid market data context fixture."""

    current_price = 100.0
    moving_avg_20d = current_price / (1 + price_vs_ma20_pct / 100) if price_vs_ma20_pct != -100 else 100.0
    moving_avg_50d = moving_avg_20d / (1 + ma20_vs_ma50_pct / 100) if ma20_vs_ma50_pct != -100 else moving_avg_20d

    return {
        "ticker": ticker,
        "run_date": "2026-04-08",
        "market_data_summary": {
            "history_rows": 252,
            "has_full_30d_window": True,
            "has_full_90d_window": True,
            "has_full_1y_window": True,
            "current_price": current_price,
            "price_30d_ago": 95.0,
            "pct_change_30d": return_30d,
            "avg_daily_volume_30d": 1_000_000.0,
            "volatility_30d": volatility_30d,
            "moving_avg_20d": round(moving_avg_20d, 4),
            "moving_avg_50d": round(moving_avg_50d, 4),
            "daily_return_mean_30d": return_30d / 30.0,
            "max_single_day_drop_90d": -3.0,
            "price_above_ma20": current_price >= moving_avg_20d,
            "ma20_above_ma50": moving_avg_20d >= moving_avg_50d,
            "volume_vs_30d_avg": volume_vs_30d_avg,
            "return_30d": return_30d,
            "return_90d": return_90d,
            "distance_from_52w_high_pct": distance_from_52w_high_pct,
            "distance_from_52w_low_pct": distance_from_52w_low_pct,
            "recent_drawdown_pct": recent_drawdown_pct,
            "RSI_14": rsi_14,
            "surge_or_drop_signal": surge_or_drop_signal,
        },
    }


def test_classify_stock_condition_prefers_momentum_when_trend_is_strong() -> None:
    """Strong positive trend input should classify as high momentum."""

    context = _context(
        "NVDA",
        volatility_30d=0.035,
        return_30d=18.0,
        return_90d=42.0,
        price_vs_ma20_pct=6.0,
        ma20_vs_ma50_pct=4.0,
        recent_drawdown_pct=4.0,
        distance_from_52w_high_pct=1.5,
        distance_from_52w_low_pct=75.0,
        volume_vs_30d_avg=1.4,
        rsi_14=74.0,
        surge_or_drop_signal="surge",
    )

    result = classify_stock_condition(context)

    assert result["primary_label"] == "high_momentum"


def test_stock_selection_returns_distinct_categories_when_possible(monkeypatch) -> None:
    """Representative selection should pick unique tickers for different categories."""

    fixtures = {
        "KO": _context(
            "KO",
            volatility_30d=0.008,
            return_30d=1.0,
            return_90d=2.0,
            price_vs_ma20_pct=0.5,
            ma20_vs_ma50_pct=0.4,
            recent_drawdown_pct=2.0,
            distance_from_52w_high_pct=4.0,
            distance_from_52w_low_pct=10.0,
            volume_vs_30d_avg=0.95,
            rsi_14=52.0,
            surge_or_drop_signal="neutral",
        ),
        "NVDA": _context(
            "NVDA",
            volatility_30d=0.04,
            return_30d=19.0,
            return_90d=45.0,
            price_vs_ma20_pct=7.0,
            ma20_vs_ma50_pct=5.0,
            recent_drawdown_pct=3.0,
            distance_from_52w_high_pct=1.0,
            distance_from_52w_low_pct=85.0,
            volume_vs_30d_avg=1.5,
            rsi_14=76.0,
            surge_or_drop_signal="surge",
        ),
        "NKE": _context(
            "NKE",
            volatility_30d=0.025,
            return_30d=-16.0,
            return_90d=-21.0,
            price_vs_ma20_pct=-8.0,
            ma20_vs_ma50_pct=-6.0,
            recent_drawdown_pct=20.0,
            distance_from_52w_high_pct=28.0,
            distance_from_52w_low_pct=6.0,
            volume_vs_30d_avg=1.1,
            rsi_14=28.0,
            surge_or_drop_signal="drop",
        ),
        "T": _context(
            "T",
            volatility_30d=0.01,
            return_30d=0.3,
            return_90d=1.1,
            price_vs_ma20_pct=0.2,
            ma20_vs_ma50_pct=0.1,
            recent_drawdown_pct=1.5,
            distance_from_52w_high_pct=5.0,
            distance_from_52w_low_pct=8.0,
            volume_vs_30d_avg=1.0,
            rsi_14=50.0,
            surge_or_drop_signal="neutral",
        ),
    }

    monkeypatch.setattr("src.stock_selector.build_market_data_context", lambda ticker: fixtures[ticker])

    report = select_representative_stocks(["KO", "NVDA", "NKE", "T"], min_count=4)

    assert report["evaluated_count"] == 4
    assert len(report["selected"]) == 4

    categories = [item["category"] for item in report["selected"]]
    tickers = [item["ticker"] for item in report["selected"]]

    assert categories == [
        "steady_large_cap",
        "high_momentum",
        "recent_decline",
        "sideways_low_direction",
    ]
    assert len(set(tickers)) == 4
