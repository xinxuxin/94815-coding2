# StockTrader

Scaffold for the assignment "Building StockTrader: Signals, Strategies, and Disagreement."

This repository is intentionally in a planning-and-scaffolding state. The project layout, design decisions, prompts, schemas, and implementation plan are locked, but the full end-to-end system has not been implemented yet.

## Locked Decisions

- Python `3.11+`
- Orchestration: `LangGraph`
- Market data: `yfinance`
- LLM access: Groq via OpenAI-compatible API by default
- Provider abstraction: Groq, OpenAI, or Ollama
- Structured outputs: `Pydantic`
- Core strategies: `Momentum Trader` vs `Value Contrarian`
- Bonus extension: `Debate Mode` on disagreement only

## Assignment Scope

The core assignment will build exactly two independent strategy agents that:

- receive the same market data payload,
- do not see each other's output before evaluation,
- emit structured recommendations,
- feed into an evaluator that produces either a consensus summary or a disagreement analysis,
- save one JSON per stock plus `summary.json`.

The bonus extension will add Debate Mode only after a disagreement is detected.

## Planned Layout

```text
stocktrader/
  README.md
  DESIGN.md
  requirements.txt
  .env.example
  src/
  prompts/
  outputs/
  report/
  tests/
```

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set the provider credentials you intend to use.

## Current Status

- Project structure is scaffolded.
- Prompt templates are stubbed.
- Schemas and module boundaries are defined.
- No live stock runs have been executed yet.
- No report content or grading outputs have been fabricated.

## Expected Deliverables

The final submission should include:

- source code under `src/`,
- prompt files under `prompts/`,
- pre-generated grading outputs under `outputs/`,
- `report/report.pdf`,
- AI use appendix PDF,
- a grading-friendly `README.md`.

## Notes for the Next Phase

- Keep the implementation simple and assignment-aligned.
- Do not widen into portfolio optimization or historical backtesting for the core system.
- Preserve the independence of the two strategy branches before evaluation.
