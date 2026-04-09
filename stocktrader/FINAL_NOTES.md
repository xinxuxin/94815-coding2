# Final Notes

## What Was Run Live

- Final grading outputs in `outputs/` were generated from real market data and live OpenAI API calls.
- The final selected stocks were `JNJ`, `XOM`, `TSLA`, `PFE`, and `NKE`.
- `summary.json`, `report.md`, `ai_use_appendix.md`, `report.pdf`, and `ai_use_appendix.pdf` were generated from those saved live outputs.

## What Was Mocked During Development

- Unit tests for the strategy agents, evaluator, and LangGraph pipeline used the repository’s deterministic `mock` provider.
- Mock runs were used to verify structured parsing, repair behavior, graph routing, summary generation, and JSON persistence without requiring API access.
- Mock development runs were kept separate from the final grading outputs.

## Remaining Limitations

- Final outputs depend on current market data and the exact LLM behavior at the time they were generated, so rerunning the same code later may produce different recommendations or wording.
- The project targets Python 3.11+, but the final hardening pass was validated in the current local environment as well.
- The selector is intentionally simple and data-driven, so “representative” stock choices are only as good as the current feature thresholds and candidate pool.
