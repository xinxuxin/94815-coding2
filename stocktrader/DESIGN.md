# Design Note

## Core Strategy Pairing

The core assignment uses:

- Strategy A: `Momentum Trader`
- Strategy B: `Value Contrarian`

This pairing is intentionally high-contrast. Both strategies can rely on the same `yfinance`-derived market data, but they interpret price action differently:

- Momentum favors strength, continuation, rising moving averages, and supportive volume.
- Value Contrarian looks for overreaction, mean-reversion opportunities, drawdowns, and potential overheating near highs.

This makes it easier to produce meaningful agreement on stable names and sharp disagreement on fast-moving or recently shocked stocks.

## Bonus Choice: Debate Mode

The chosen bonus is `Debate Mode`, triggered only when the evaluator detects disagreement.

Reasons for choosing it now:

- it extends the required agent comparison without changing the core grading path,
- it keeps the system intellectually aligned with the assignment's emphasis on disagreement,
- it is simpler and lower-risk than adding a third core agent or a historical scorecard.

Debate Mode will remain an optional second-round branch after the main evaluator decision.

## Intended Graph Flow

```text
START
  |
  v
Market Data Node
  |
  +---------------------+
  |                     |
  v                     v
Strategy A Node     Strategy B Node
  |                     |
  +----------+----------+
             |
             v
        Evaluator Node
             |
      +------+------+
      |             |
      v             v
   Agreement     Disagreement
                     |
                     v
               Debate Mode Branch
                     |
                     v
                  Save Outputs
```

Implementation intent:

- the market data payload is computed once,
- both strategy nodes consume the same normalized payload,
- neither strategy reads the other's result,
- the evaluator decides whether to produce consensus or disagreement analysis,
- Debate Mode runs only when `agents_agree == false`,
- the final output writer saves one stock JSON plus aggregated `summary.json`.

## Exact Deliverables

The final repository should contain:

- `src/` with orchestration, market data, strategy, evaluator, config, utility, and schema modules,
- `prompts/` with strategy, evaluator, and debate prompt text files,
- `outputs/` with one JSON per stock and `summary.json`,
- `report/report.pdf`,
- AI use appendix PDF,
- `README.md`,
- `requirements.txt`,
- `.env.example`.

## Important Assumptions

- Python runtime target is `3.11+`.
- Groq is the default provider, accessed through the OpenAI-compatible client shape.
- Provider selection is environment-driven.
- Pydantic models are the source of truth for structured LLM input/output contracts.
- Pre-generated outputs will be included later for grading, but are intentionally not generated during this scaffolding phase.
