"""Data-driven stock classification and representative selection."""

from __future__ import annotations

from typing import Any, Optional

from .market_data import build_market_data_context
from .schemas import MarketDataContext


CANDIDATE_UNIVERSE = [
    "MSFT",
    "JNJ",
    "KO",
    "PG",
    "NVDA",
    "TSLA",
    "AMD",
    "NKE",
    "PFE",
    "XOM",
    "T",
    "GME",
]

CATEGORY_ORDER = [
    "steady_large_cap",
    "high_momentum",
    "recent_decline",
    "sideways_low_direction",
]


def classify_stock_condition(context: dict[str, Any]) -> dict[str, Any]:
    """Classify one stock context into assignment-relevant market conditions."""

    validated = MarketDataContext.model_validate(context)
    summary = validated.market_data_summary

    price_vs_ma20_pct = _pct_gap(summary.current_price, summary.moving_avg_20d)
    ma_spread_pct = _pct_gap(summary.moving_avg_20d, summary.moving_avg_50d)
    abs_return_30d = abs(summary.return_30d)
    abs_return_90d = abs(summary.return_90d)
    abs_daily_mean = abs(summary.daily_return_mean_30d)
    max_drop_abs = abs(min(summary.max_single_day_drop_90d, 0.0))

    scores = {
        "steady_large_cap": round(
            _inverse_score(summary.volatility_30d, scale=0.03) * 0.35
            + _inverse_score(abs_return_30d, scale=8.0) * 0.25
            + _inverse_score(max_drop_abs, scale=6.0) * 0.20
            + _inverse_score(price_vs_ma20_pct, scale=4.0) * 0.20,
            4,
        ),
        "high_momentum": round(
            _positive_score(summary.return_30d, scale=15.0) * 0.35
            + _positive_score(summary.return_90d, scale=25.0) * 0.25
            + (0.15 if summary.price_above_ma20 else 0.0)
            + (0.15 if summary.ma20_above_ma50 else 0.0)
            + _positive_score(summary.volume_vs_30d_avg - 1.0, scale=0.5) * 0.10,
            4,
        ),
        "recent_decline": round(
            _positive_score(-summary.return_30d, scale=12.0) * 0.35
            + _positive_score(summary.recent_drawdown_pct, scale=18.0) * 0.30
            + _positive_score(summary.distance_from_52w_high_pct, scale=25.0) * 0.20
            + (0.15 if summary.surge_or_drop_signal == "drop" else 0.0),
            4,
        ),
        "sideways_low_direction": round(
            _inverse_score(abs_return_30d, scale=6.0) * 0.30
            + _inverse_score(abs_return_90d, scale=10.0) * 0.20
            + _inverse_score(price_vs_ma20_pct, scale=3.0) * 0.20
            + _inverse_score(ma_spread_pct, scale=3.0) * 0.20
            + _inverse_score(abs_daily_mean, scale=0.8) * 0.10,
            4,
        ),
    }

    primary_label = max(scores, key=scores.get)
    metrics = {
        "volatility_30d": summary.volatility_30d,
        "return_30d": summary.return_30d,
        "return_90d": summary.return_90d,
        "daily_return_mean_30d": summary.daily_return_mean_30d,
        "recent_drawdown_pct": summary.recent_drawdown_pct,
        "distance_from_52w_high_pct": summary.distance_from_52w_high_pct,
        "distance_from_52w_low_pct": summary.distance_from_52w_low_pct,
        "volume_vs_30d_avg": summary.volume_vs_30d_avg,
        "price_vs_ma20_pct": round(price_vs_ma20_pct, 4),
        "ma20_vs_ma50_pct": round(ma_spread_pct, 4),
        "RSI_14": summary.RSI_14,
        "surge_or_drop_signal": summary.surge_or_drop_signal,
    }

    return {
        "ticker": validated.ticker,
        "primary_label": primary_label,
        "scores": scores,
        "metrics": metrics,
    }


def select_representative_stocks(
    candidate_list: Optional[list[str]] = None,
    min_count: int = 4,
) -> dict[str, Any]:
    """Select distinct representative stocks from the fixed candidate pool."""

    candidates = candidate_list or CANDIDATE_UNIVERSE
    evaluations: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for ticker in candidates:
        try:
            context = build_market_data_context(ticker)
            classification = classify_stock_condition(context)
            classification["context"] = context
            evaluations.append(classification)
        except Exception as exc:  # pragma: no cover - exercised only on live fetch failures
            failures.append({"ticker": ticker, "error": str(exc)})

    selected: list[dict[str, Any]] = []
    selected_tickers: set[str] = set()

    for category in CATEGORY_ORDER:
        ranked = sorted(
            evaluations,
            key=lambda item: item["scores"][category],
            reverse=True,
        )
        chosen = next((item for item in ranked if item["ticker"] not in selected_tickers), None)
        if chosen is None:
            continue

        selected.append(
            {
                "category": category,
                "ticker": chosen["ticker"],
                "score": chosen["scores"][category],
                "why_selected": _selection_reason(category, chosen["metrics"]),
                "metrics": chosen["metrics"],
            }
        )
        selected_tickers.add(chosen["ticker"])

    if len(selected) < min_count:
        remaining = [item for item in evaluations if item["ticker"] not in selected_tickers]
        remaining.sort(key=lambda item: max(item["scores"].values()), reverse=True)
        for item in remaining:
            if len(selected) >= min_count:
                break
            best_category = max(item["scores"], key=item["scores"].get)
            selected.append(
                {
                    "category": f"additional_{best_category}",
                    "ticker": item["ticker"],
                    "score": item["scores"][best_category],
                    "why_selected": _selection_reason(best_category, item["metrics"]),
                    "metrics": item["metrics"],
                }
            )
            selected_tickers.add(item["ticker"])

    return {
        "candidate_pool": candidates,
        "evaluated_count": len(evaluations),
        "selected": selected,
        "classifications": [
            {
                "ticker": item["ticker"],
                "primary_label": item["primary_label"],
                "scores": item["scores"],
                "metrics": item["metrics"],
            }
            for item in evaluations
        ],
        "failures": failures,
    }


def _selection_reason(category: str, metrics: dict[str, Any]) -> str:
    """Create a short, data-driven selection explanation for one category."""

    if category == "steady_large_cap":
        return (
            "Selected for low volatility, mild 30-day movement, small price-to-MA gap, "
            f"and limited worst one-day drop ({metrics['volatility_30d']}, "
            f"{metrics['return_30d']}%, {metrics['price_vs_ma20_pct']}%)."
        )
    if category == "high_momentum":
        return (
            "Selected for strong positive returns, supportive moving-average alignment, "
            f"and elevated volume signal ({metrics['return_30d']}%, {metrics['return_90d']}%, "
            f"volume ratio {metrics['volume_vs_30d_avg']})."
        )
    if category == "recent_decline":
        return (
            "Selected for negative recent performance and drawdown pressure "
            f"({metrics['return_30d']}%, drawdown {metrics['recent_drawdown_pct']}%, "
            f"signal {metrics['surge_or_drop_signal']})."
        )
    return (
        "Selected for low directional drift and tight moving-average spread "
        f"({metrics['return_30d']}%, {metrics['return_90d']}%, "
        f"MA spread {metrics['ma20_vs_ma50_pct']}%)."
    )


def _pct_gap(current: float, reference: float) -> float:
    """Return signed percentage gap between two values."""

    if reference == 0:
        return 0.0
    return ((current - reference) / reference) * 100.0


def _inverse_score(value: float, scale: float) -> float:
    """Higher score for smaller-magnitude values."""

    value = abs(float(value))
    if scale <= 0:
        return 0.0
    return 1.0 / (1.0 + (value / scale))


def _positive_score(value: float, scale: float) -> float:
    """Higher score for larger positive values."""

    if scale <= 0:
        return 0.0
    return max(0.0, min(float(value) / scale, 1.0))
