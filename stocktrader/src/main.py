"""CLI entry point for the StockTrader assignment workflow."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from .config import Settings, get_settings
from .market_data import build_market_data_context
from .orchestration import (
    render_architecture_diagram,
    run_pipeline_for_ticker,
    run_pipeline_for_tickers,
)
from .stock_selector import CANDIDATE_UNIVERSE, select_representative_stocks
from .strategy_agents import run_momentum_agent, run_value_contrarian_agent


def main() -> None:
    """Provide a simple CLI for the assignment workflow."""

    _configure_logging()
    parser = argparse.ArgumentParser(description="StockTrader assignment CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the full pipeline for one ticker")
    run_parser.add_argument("--ticker", required=True, help="Ticker symbol to analyze")
    run_parser.add_argument("--mock", action="store_true", help="Force deterministic mock mode")

    run_many_parser = subparsers.add_parser(
        "run-many",
        help="Run the full pipeline for multiple tickers or auto-selected representatives",
    )
    run_many_parser.add_argument("--tickers", nargs="*", help="Optional explicit ticker list")
    run_many_parser.add_argument("--mock", action="store_true", help="Force deterministic mock mode")

    select_parser = subparsers.add_parser(
        "select-stocks",
        help="Show the data-driven representative stock selection report",
    )
    select_parser.add_argument(
        "--tickers",
        nargs="*",
        default=CANDIDATE_UNIVERSE,
        help="Optional candidate pool override",
    )

    render_parser = subparsers.add_parser(
        "render-report",
        help="Generate the architecture diagram artifact for the report",
    )
    render_parser.add_argument(
        "--output-root",
        default=None,
        help="Optional project root override for tests or alternate workspaces",
    )

    context_parser = subparsers.add_parser("context", help="Show market data context for tickers")
    context_parser.add_argument("tickers", nargs="+", help="Ticker symbols to inspect")

    agents_parser = subparsers.add_parser("agents", help="Run the two core strategy agents only")
    agents_parser.add_argument("ticker", help="Ticker symbol to inspect")
    agents_parser.add_argument("--mock", action="store_true", help="Force deterministic mock mode")

    args = parser.parse_args()

    if args.command == "run":
        settings = _resolve_agent_settings(force_mock=args.mock)
        output = run_pipeline_for_ticker(args.ticker, settings=settings)
        print(json.dumps(output.model_dump(), indent=2))
        return

    if args.command == "run-many":
        settings = _resolve_agent_settings(force_mock=args.mock)
        tickers = args.tickers
        if not tickers:
            selection_report = select_representative_stocks(CANDIDATE_UNIVERSE)
            tickers = [item["ticker"] for item in selection_report["selected"]]
        summary = run_pipeline_for_tickers(tickers=tickers, settings=settings)
        print(json.dumps(summary.model_dump(), indent=2))
        return

    if args.command == "select-stocks":
        report = select_representative_stocks(args.tickers)
        print(json.dumps(report, indent=2))
        return

    if args.command == "render-report":
        output_root = Path(args.output_root) if args.output_root else None
        path = render_architecture_diagram(project_root=output_root)
        print(str(path))
        return

    if args.command == "context":
        payload = [build_market_data_context(ticker) for ticker in args.tickers]
        print(json.dumps(payload, indent=2))
        return

    if args.command == "agents":
        context = build_market_data_context(args.ticker)
        runtime_settings = _resolve_agent_settings(force_mock=args.mock)
        payload = {
            "mode": "mock" if runtime_settings.llm_provider == "mock" else "live",
            "provider": runtime_settings.llm_provider,
            "ticker": args.ticker.upper(),
            "market_data_context": context,
            "strategy_a": run_momentum_agent(context, settings=runtime_settings).model_dump(),
            "strategy_b": run_value_contrarian_agent(context, settings=runtime_settings).model_dump(),
        }
        print(json.dumps(payload, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


def _resolve_agent_settings(force_mock: bool = False) -> Settings:
    """Return live settings when available, otherwise fall back to deterministic mock mode."""

    current = get_settings()
    if force_mock:
        return Settings(llm_provider="mock")
    if current.llm_provider == "mock":
        return current
    if current.has_live_credentials():
        return current
    return Settings(llm_provider="mock")


def _configure_logging() -> None:
    """Set up a lightweight console logger."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


if __name__ == "__main__":
    main()
