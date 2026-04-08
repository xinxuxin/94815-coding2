"""Tiny CLI for market-data smoke checks."""

from __future__ import annotations

import argparse
import json

from .market_data import build_market_data_context
from .stock_selector import CANDIDATE_UNIVERSE, select_representative_stocks


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

    args = parser.parse_args()

    if args.command == "context":
        payload = [build_market_data_context(ticker) for ticker in args.tickers]
        print(json.dumps(payload, indent=2))
        return

    if args.command == "select":
        report = select_representative_stocks(args.tickers)
        print(json.dumps(report, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
