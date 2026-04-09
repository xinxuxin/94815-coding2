# AI Use Appendix

## Representative Development Prompts

During development I used the following representative prompts and instruction patterns:

1. **Momentum Trader system prompt**: emphasize price relative to 20-day and 50-day moving averages, recent returns, and volume confirmation; output strict JSON only.
2. **Value Contrarian system prompt**: emphasize drawdown, distance from 52-week extremes, RSI, and overreaction; output strict JSON only.
3. **Evaluator prompt**: compare strategy philosophies and identify the real source of divergence instead of restating labels.
4. **Debate prompts**: let each strategy produce one short rebuttal while staying faithful to its original philosophy.

## Short Output Excerpts

Example strategy excerpt from `TSLA.json`:

> "The current price of TSLA at 343.25 is below both the 20-day moving average of 376.26 and the 50-day moving average of 397.66, indicating a bearish trend. Additionally, the recent 30-day return is -16.15%, which shows significant deterioration in performance. The RSI is also low at 31.99, suggesting that the stock is oversold. Given these factors, the trend alignment is broken, and the price action is weak, warranting a sell decision."

Example evaluator excerpt from `TSLA.json`:

> "The two strategies diverge significantly in their recommendations. Strategy A, the Momentum Trader, advocates for a SELL based on the bearish trend indicated by the current price being below both moving averages and a negative 30-day return. In contrast, Strategy B, the Value Contrarian, suggests a BUY, arguing that the stock is oversold and undervalued given its distance from the 52-week high and the same low RSI reading. The divergence stems from their differing philosophies: one focuses on trend-following evidence while the other emphasizes mean-reversion and value assessment."

Example debate excerpt from `TSLA.json`:

> "The Momentum Trader's focus on moving averages and recent performance overlooks the deeper value indicators present in TSLA's current situation. The significant distance from the 52-week high and the oversold RSI at 31.99 suggest that the stock is not just experiencing a temporary dip but is undervalued due to market overreaction. The 29.93% recent drawdown reflects panic rather than a fundamental deterioration in value, making this an opportune time to buy."

## What I Accepted

- The strict JSON output shape from the strategy, evaluator, and debate components.
- The market-data feature set because it supported both strategies without requiring a second data source.
- The Debate Mode branch because it stayed within scope while strengthening the disagreement analysis.

## What I Revised

- I tightened validation so justifications had to contain 3 to 5 sentences and at least two numeric facts.
- I added a repair path for malformed JSON instead of silently accepting weak model output.
- I separated mock-backed tests from final live outputs so grading artifacts would remain honest.
- I added a report renderer so the repository produces actual PDFs instead of markdown only.

## What I Rejected

- Adding portfolio optimization or broader trading infrastructure, because that would violate the scope warning.
- Treating mock runs as final grading outputs.
- Letting one strategy see the other strategy’s output before evaluation.

## What I Verified Independently

- Indicator calculations and stock selection logic with synthetic tests.
- Schema validity for strategy, evaluator, and debate outputs.
- Full mock-backed LangGraph integration tests for save flow and summary generation.
- Final grading outputs were generated from live market data and live LLM calls rather than fabricated examples.
