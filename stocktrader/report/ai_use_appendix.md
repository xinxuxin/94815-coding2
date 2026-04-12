# AI Use Appendix

## Purpose of This Appendix

This appendix documents how generative AI was used during the development of the StockTrader project. It is intended to show where AI assistance was used, what kinds of outputs it produced, and what editorial judgment was applied before any content was retained in the final submission.

AI was used in four limited ways during this project: prompt drafting and refinement, runtime decision generation for the two strategy agents and evaluator, structured-output hardening for JSON-based outputs, and writing support during reporting. The final submission was still shaped by explicit human decisions about architecture, validation, stock selection logic, rejection of weak ideas, and acceptance only after checking alignment with the assignment requirements.

## Representative Development Prompts

### 1. Momentum Trader system prompt

The Momentum Trader prompt was designed to make the model reason like a trend-following investor. It emphasized recent price direction, moving-average alignment, recent returns, and volume confirmation, and it instructed the model to return strict structured JSON only.

Representative phrasing:

> "You are a Momentum Trader. Use the provided market data summary to make exactly one decision: BUY, HOLD, or SELL. Prioritize trend alignment, 20-day and 50-day moving averages, recent returns, and volume confirmation. Prefer buying strength and selling weakness. Reference specific numeric facts from the input. Return strict JSON with fields: decision, confidence, justification."

### 2. Value Contrarian system prompt

The Value Contrarian prompt was designed to push the model toward the opposite interpretation. It emphasized drawdown, distance from the 52-week high, and RSI as signs of possible overreaction and instructed the model to look for buying opportunities when the market appeared oversold.

Representative phrasing:

> "You are a Value Contrarian investor. Use the market data summary to make exactly one decision: BUY, HOLD, or SELL. Prioritize drawdown, distance from 52-week extremes, and RSI. Look for signs that the market may be overreacting. Reference specific numeric facts from the input. Return strict JSON with fields: decision, confidence, justification."

### 3. Evaluator prompt

The evaluator prompt was written to prevent shallow comparisons. It instructed the model to identify the real source of agreement or disagreement between the two strategies rather than merely restating their labels.

Representative phrasing:

> "Compare the outputs of the Momentum Trader and Value Contrarian for the same stock. If they agree, explain why their different philosophies still converged on the same decision. If they disagree, identify the real source of divergence in how they interpret the same evidence. Do not merely restate their labels. Return structured output with agents_agree and analysis."

### 4. Debate prompts for the bonus extension

The Debate Mode prompts were designed to preserve the original decisions while allowing one short rebuttal turn per strategy after a disagreement. The goal was not to force convergence, but to reveal whether the disagreement was shallow or durable.

Representative phrasing:

> "You are the Momentum Trader responding to the Value Contrarian's reasoning. Defend your original decision in one short rebuttal. Do not change your original label. Stay faithful to your philosophy and refer to the same market data."

> "You are the Value Contrarian responding to the Momentum Trader's reasoning. Defend your original decision in one short rebuttal. Do not change your original label. Stay faithful to your philosophy and refer to the same market data."

## Short Output Excerpts

### Excerpt 1: Momentum Trader on TSLA

> "The current price of TSLA at 343.25 is below both the 20-day moving average of 376.26 and the 50-day moving average of 397.66, indicating a bearish trend. Additionally, the recent 30-day return is -16.15%, which shows significant deterioration in performance. The RSI is also low at 31.99, suggesting that the stock is oversold. Given these factors, the trend alignment is broken, and the price action is weak, warranting a sell decision."

Why this excerpt was kept: it grounded the `SELL` decision in specific numbers, used the indicators the prompt asked it to prioritize, and clearly reflected a momentum-style interpretation of the same evidence.

### Excerpt 2: Evaluator analysis on TSLA disagreement

> "The two strategies diverge significantly in their recommendations. Strategy A, the Momentum Trader, advocates for a SELL based on the bearish trend indicated by the current price being below both moving averages and a negative 30-day return. In contrast, Strategy B, the Value Contrarian, suggests a BUY, arguing that the stock is oversold and undervalued given its distance from the 52-week high and the same low RSI reading. The divergence stems from their differing philosophies: one focuses on trend-following evidence while the other emphasizes mean-reversion and value assessment."

Why this excerpt was kept: it did more than summarize the labels. It identified the actual source of divergence, which is the core analytical requirement of the assignment.

### Excerpt 3: Value Contrarian rebuttal in Debate Mode

> "The Momentum Trader's focus on moving averages and recent performance overlooks the deeper value indicators present in TSLA's current situation. The significant distance from the 52-week high and the oversold RSI at 31.99 suggest that the stock is not just experiencing a temporary dip but is undervalued due to market overreaction. The 29.93% recent drawdown reflects panic rather than a fundamental deterioration in value, making this an opportune time to buy."

Why this excerpt was kept: it showed that the bonus debate layer was not redundant. The rebuttal made the philosophical split more explicit while preserving the original decision.

## Accepted, Revised, Rejected, and Verified Independently

### Accepted

Accepted elements included strict JSON output contracts, a shared market-data payload for both strategy agents, and Debate Mode as the bonus extension. These choices directly improved assignment compliance by keeping the two strategies behaviorally distinct while making downstream validation easier.

### Revised

Several pieces were revised after early AI outputs proved too weak or too generic. The main revisions were stronger output validation, a repair-on-invalid-JSON step, tighter strategy prompt wording, and a reporting pipeline that produced actual PDF deliverables instead of leaving the submission at the markdown stage.

### Rejected

Rejected ideas included portfolio optimization, fabricated grading outputs, and any design in which one strategy could see the other strategy's output before evaluation. These were excluded because they either violated the project scope or weakened the required independence of the two strategy branches.

### Verified Independently

Indicator calculations such as moving averages, drawdown, returns, and RSI were verified in Python code. Output JSON files were checked against Pydantic schemas. Integration tests verified evaluator routing and disagreement-triggered debate logic. Final report claims about agreement, disagreement, and the surprise case were checked against the saved JSON outputs rather than accepted blindly from model-generated prose.

## Editorial Judgment Summary

The final submission should not be understood as unedited model output. AI was used as a development and runtime tool, but acceptance was selective. Weak outputs were revised or discarded, implementation details were validated in code, and the final analytical framing was based on evidence in the saved outputs. AI accelerated drafting and experimentation, but the final submission depended on explicit human judgment about what counted as compliant, well-grounded, and worth keeping.
