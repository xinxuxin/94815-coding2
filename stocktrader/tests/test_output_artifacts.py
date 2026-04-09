"""Validate committed output artifacts against repository schemas."""

from __future__ import annotations

import json
from pathlib import Path

from src.schemas import StockRunOutput, SummaryOutput


def test_output_files_validate_against_schemas() -> None:
    """All committed per-stock JSON artifacts should validate cleanly."""

    root = Path(__file__).resolve().parents[1] / "outputs"
    tickers = ["JNJ", "XOM", "TSLA", "PFE", "NKE"]

    for ticker in tickers:
        payload = json.loads((root / f"{ticker}.json").read_text(encoding="utf-8"))
        validated = StockRunOutput.model_validate(payload)
        assert validated.ticker == ticker


def test_summary_counts_match_per_stock_outputs() -> None:
    """summary.json counts should match the actual per-stock files."""

    root = Path(__file__).resolve().parents[1] / "outputs"
    summary = SummaryOutput.model_validate(
        json.loads((root / "summary.json").read_text(encoding="utf-8"))
    )

    outputs = [
        StockRunOutput.model_validate(
            json.loads((root / f"{ticker}.json").read_text(encoding="utf-8"))
        )
        for ticker in summary.stocks_analyzed
    ]
    agreements = sum(1 for output in outputs if output.evaluator.agents_agree)
    disagreements = len(outputs) - agreements

    assert summary.total_agreements == agreements
    assert summary.total_disagreements == disagreements
