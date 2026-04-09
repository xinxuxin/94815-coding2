"""Integration tests for the full LangGraph pipeline using mock LLM responses."""

from __future__ import annotations

import json

from src.config import Settings
from src.orchestration import (
    build_summary_output,
    render_architecture_diagram,
    run_pipeline_for_ticker,
    run_pipeline_for_tickers,
)


def _base_context(
    ticker: str,
    *,
    return_30d: float,
    return_90d: float,
    price_above_ma20: bool,
    ma20_above_ma50: bool,
    volume_vs_30d_avg: float,
    drawdown: float,
    rsi: float,
    signal: str,
    distance_from_52w_high_pct: float = 24.0,
    distance_from_52w_low_pct: float = 8.0,
) -> dict:
    """Return a compact market context fixture for pipeline tests."""

    current_price = 100.0
    ma20 = 95.0 if price_above_ma20 else 104.0
    ma50 = 92.0 if ma20_above_ma50 else 108.0
    return {
        "ticker": ticker,
        "run_date": "2026-04-08",
        "market_data_summary": {
            "history_rows": 252,
            "has_full_30d_window": True,
            "has_full_90d_window": True,
            "has_full_1y_window": True,
            "current_price": current_price,
            "price_30d_ago": round(current_price / (1 + return_30d / 100.0), 4) if return_30d != -100 else 100.0,
            "pct_change_30d": return_30d,
            "avg_daily_volume_30d": 1000000.0,
            "volatility_30d": 0.02,
            "moving_avg_20d": ma20,
            "moving_avg_50d": ma50,
            "daily_return_mean_30d": round(return_30d / 30.0, 4),
            "max_single_day_drop_90d": -5.2,
            "price_above_ma20": price_above_ma20,
            "ma20_above_ma50": ma20_above_ma50,
            "volume_vs_30d_avg": volume_vs_30d_avg,
            "return_30d": return_30d,
            "return_90d": return_90d,
            "distance_from_52w_high_pct": distance_from_52w_high_pct,
            "distance_from_52w_low_pct": distance_from_52w_low_pct,
            "recent_drawdown_pct": drawdown,
            "RSI_14": rsi,
            "surge_or_drop_signal": signal,
        },
    }


def test_full_pipeline_saves_per_ticker_json(monkeypatch, tmp_path) -> None:
    """A single-ticker run should produce a grading-friendly JSON file."""

    context = _base_context(
        "TSLA",
        return_30d=-9.5,
        return_90d=-14.2,
        price_above_ma20=False,
        ma20_above_ma50=False,
        volume_vs_30d_avg=0.9,
        drawdown=18.3,
        rsi=29.5,
        signal="drop",
    )
    monkeypatch.setattr("src.orchestration.build_market_data_context", lambda ticker: context)

    output = run_pipeline_for_ticker("TSLA", settings=Settings(llm_provider="mock"), project_root=tmp_path)

    output_path = tmp_path / "outputs" / "TSLA.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "TSLA"
    assert payload["evaluator"]["agents_agree"] is False
    assert payload["debate_mode"]["triggered"] is True
    assert output.post_debate_synthesis is not None


def test_run_many_builds_summary_json(monkeypatch, tmp_path) -> None:
    """Multi-ticker runs should persist summary.json with agreement counts."""

    contexts = {
        "TSLA": _base_context(
            "TSLA",
            return_30d=-9.5,
            return_90d=-14.2,
            price_above_ma20=False,
            ma20_above_ma50=False,
            volume_vs_30d_avg=0.9,
            drawdown=18.3,
            rsi=29.5,
            signal="drop",
        ),
        "PFE": _base_context(
            "PFE",
            return_30d=1.2,
            return_90d=6.8,
            price_above_ma20=True,
            ma20_above_ma50=True,
            volume_vs_30d_avg=0.95,
            drawdown=3.0,
            rsi=52.0,
            signal="neutral",
            distance_from_52w_high_pct=14.0,
            distance_from_52w_low_pct=22.0,
        ),
    }
    monkeypatch.setattr("src.orchestration.build_market_data_context", lambda ticker: contexts[ticker])

    summary = run_pipeline_for_tickers(
        ["TSLA", "PFE"],
        settings=Settings(llm_provider="mock"),
        project_root=tmp_path,
    )

    summary_path = tmp_path / "outputs" / "summary.json"
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["strategies"] == ["Momentum Trader", "Value Contrarian"]
    assert set(payload["stocks_analyzed"]) == {"TSLA", "PFE"}
    assert payload["total_disagreements"] == 1
    assert payload["total_agreements"] == 1
    assert summary.total_agreements == 1


def test_render_architecture_diagram_creates_png(tmp_path) -> None:
    """The report diagram artifact should be generated for grading/report use."""

    path = render_architecture_diagram(project_root=tmp_path)
    assert path.exists()
    assert path.name == "architecture_diagram.png"


def test_build_summary_output_matches_assignment_shape(monkeypatch, tmp_path) -> None:
    """Summary aggregation should stay close to the assignment example."""

    contexts = {
        "TSLA": _base_context(
            "TSLA",
            return_30d=-9.5,
            return_90d=-14.2,
            price_above_ma20=False,
            ma20_above_ma50=False,
            volume_vs_30d_avg=0.9,
            drawdown=18.3,
            rsi=29.5,
            signal="drop",
        ),
        "PFE": _base_context(
            "PFE",
            return_30d=1.2,
            return_90d=6.8,
            price_above_ma20=True,
            ma20_above_ma50=True,
            volume_vs_30d_avg=0.95,
            drawdown=3.0,
            rsi=52.0,
            signal="neutral",
            distance_from_52w_high_pct=14.0,
            distance_from_52w_low_pct=22.0,
        ),
    }
    monkeypatch.setattr("src.orchestration.build_market_data_context", lambda ticker: contexts[ticker])
    first = run_pipeline_for_ticker("TSLA", settings=Settings(llm_provider="mock"), project_root=tmp_path)
    second = run_pipeline_for_ticker("PFE", settings=Settings(llm_provider="mock"), project_root=tmp_path)

    summary = build_summary_output([first, second]).model_dump()
    assert "strategies" in summary
    assert "stocks_analyzed" in summary
    assert "results" in summary
    assert all(set(row.keys()) == {"ticker", "a_decision", "b_decision", "agree"} for row in summary["results"])
