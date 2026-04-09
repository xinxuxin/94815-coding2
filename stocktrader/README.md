# StockTrader

`StockTrader` is a grading-friendly implementation of the assignment **“Building StockTrader: Signals, Strategies, and Disagreement.”** The system fetches real market data with `yfinance`, runs two independent LLM strategy agents on the same input, compares their recommendations, optionally runs Debate Mode on disagreement, and saves one JSON artifact per stock plus `summary.json`.

## Assignment Overview

The assignment asks for:

- one non-LLM market data component,
- exactly two independent strategy agents,
- one evaluator that explains agreement or disagreement,
- one bonus extension,
- pre-generated outputs so grading does not require rerunning the system or providing an API key.

This repository stays within that scope. It does **not** add portfolio optimization or full historical backtesting to the core workflow.

## Chosen Strategies

- Strategy A: `Momentum Trader`
- Strategy B: `Value Contrarian`

## Why This Pairing

This pairing creates a clear behavioral contrast while still using the same `yfinance`-derived features:

- The Momentum Trader prioritizes trend continuation, moving-average alignment, recent returns, and volume confirmation.
- The Value Contrarian prioritizes overreaction, drawdown, distance from 52-week extremes, and RSI.

That contrast makes it easier to surface both agreement and disagreement across different market conditions. In the final stock set, the two agents agreed on steadier names and split sharply on large recent drawdowns.

## Bonus Extension

The chosen bonus extension is `Debate Mode`.

- Debate Mode triggers only when the two core agents disagree.
- Each strategy gets one short rebuttal turn.
- The original strategy outputs remain unchanged.
- Debate content is stored in a separate JSON field for grading.

## LLM Provider Used

Final grading outputs in `outputs/` were generated locally with the **OpenAI ChatGPT API** using an OpenAI-compatible client interface.

Model used for final runs:

- `gpt-4o-mini`

The codebase also supports:

- `groq`
- `openai`
- `ollama`
- `mock` for tests

## Framework and Tooling

- Python `3.11+` target
- `LangGraph` for orchestration
- `yfinance` for market data
- `Pydantic` for structured validation
- `reportlab` for PDF generation
- `pytest` for unit and integration tests

## Install

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Set one provider configuration:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
```

You can also configure `groq` or `ollama`.

## Run Commands

Run one ticker:

```bash
python -m src.main run --ticker TSLA
```

Run multiple explicit tickers:

```bash
python -m src.main run-many --tickers JNJ XOM TSLA PFE NKE
```

Run the data-driven stock selector only:

```bash
python -m src.main select-stocks
```

Render the report architecture diagram:

```bash
python -m src.main render-report
```

Show market data context only:

```bash
python -m src.main context TSLA
```

Run just the two strategy agents:

```bash
python -m src.main agents TSLA
```

Run tests:

```bash
pytest -q
```

## Pre-generated Outputs

Pre-generated outputs are included in `outputs/` for grading without an API key:

- `JNJ.json`
- `XOM.json`
- `TSLA.json`
- `PFE.json`
- `NKE.json`
- `summary.json`

These files were generated from real market data and real LLM calls.

## Repository Structure

```text
stocktrader/
  README.md
  DESIGN.md
  requirements.txt
  .env.example
  src/
    main.py
    config.py
    schemas.py
    market_data.py
    strategy_agents.py
    evaluator.py
    orchestration.py
    stock_selector.py
    utils.py
    reporting.py
  prompts/
    strategy_a.txt
    strategy_b.txt
    evaluator.txt
    debate_a.txt
    debate_b.txt
  outputs/
    JNJ.json
    XOM.json
    TSLA.json
    PFE.json
    NKE.json
    summary.json
  report/
    architecture_diagram.png
    report.md
    ai_use_appendix.md
    report.pdf
    ai_use_appendix.pdf
  tests/
```

## Final Stock Set

The final selected stocks and their intended roles were:

- `JNJ`: steady established large-cap
- `XOM`: higher-momentum name with stronger 90-day trend
- `TSLA`: recent decline with clear behavioral disagreement
- `PFE`: sideways / low-direction case
- `NKE`: extra sharp drawdown case to strengthen disagreement analysis

## Submission Notes

- The two strategy agents receive the same market data payload.
- Neither strategy sees the other’s output before evaluation.
- The evaluator explicitly distinguishes agreement from disagreement.
- Debate Mode is isolated and only runs after disagreement.
- Outputs are saved in a grading-friendly JSON structure close to the assignment example.
