"""Tiny CLI for market-data smoke checks."""

from __future__ import annotations

import argparse
import json

from .config import Settings, get_settings
from .market_data import build_market_data_context
from .stock_selector import CANDIDATE_UNIVERSE, select_representative_stocks
from .strategy_agents import run_momentum_agent, run_value_contrarian_agent


def main() -> None:
    """Provide lightweight CLI access to the pure-Python data layer."""

    parser = argparse.ArgumentParser(description="StockTrader market-data smoke CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser("context", help="Show market data context for tickers")
    context_parser.add_argument("tickers", nargs="+", help="Ticker symbols to inspect")

    select_parser = subparsers.add_parser("select", help="Select representative stocks")
    select_parser.add_argument(
        "--tickers",
        nargs="*",
        default=CANDIDATE_UNIVERSE,
        help="Optional candidate pool override",
    )

    agents_parser = subparsers.add_parser("agents", help="Run the two core strategy agents")
    agents_parser.add_argument("ticker", help="Ticker symbol to inspect")
    agents_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use the deterministic mock provider even if live credentials exist",
    )

    args = parser.parse_args()

    if args.command == "context":
        payload = [build_market_data_context(ticker) for ticker in args.tickers]
        print(json.dumps(payload, indent=2))
        return

    if args.command == "select":
        report = select_representative_stocks(args.tickers)
        print(json.dumps(report, indent=2))
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


if __name__ == "__main__":
    main()
