# StockTrader Report

Comparative analysis of Momentum Trader and Value Contrarian on data-selected stocks.

- Strategies: `Momentum Trader` vs `Value Contrarian`
- Stocks: `JNJ`, `XOM`, `TSLA`, `PFE`, `NKE`
- Outcome: `3` agreements, `2` disagreements

## Strategy Selection and Rationale

This project uses `Momentum Trader` versus `Value Contrarian` as the two required core agents. This pairing was chosen because the strategies are behaviorally distinct rather than cosmetically different. The Momentum Trader rewards continuation: it interprets price above key moving averages, supportive recent returns, and volume confirmation as evidence that the trend remains intact. The Value Contrarian begins from the opposite behavioral premise. It assumes that markets frequently overreact, so sharp sell-offs, large drawdowns, and oversold technical readings can represent buying opportunities rather than confirmation of further decline.

This pairing is also useful experimentally because the assignment is not primarily about profitability; it is about whether two agents, grounded in the same market data, can produce meaningfully different judgments and whether those differences can be explained clearly. A stock trading well below recent moving averages can look like a broken trend to momentum logic but like a discounted opportunity to mean-reversion logic.

Before running the system, I expected the cleanest disagreement cases to appear in names with sharp recent declines. In those environments, the Momentum Trader should read weakness as continued downside risk, while the Value Contrarian should read the same weakness as evidence of overreaction. I expected more convergence in steadier or lower-direction stocks because neither continuation nor mean-reversion would be strong enough to dominate. The final results broadly confirmed that hypothesis. The strategies converged on three moderate or balanced cases and split decisively on two heavy-drawdown cases, which suggests that the system succeeded in surfacing real behavioral differences rather than prompt wording noise.

## System Architecture

The architecture follows the assignment workflow directly: `ticker -> market data -> two independent strategy branches -> evaluator -> optional debate -> save JSON`. The design emphasis is separation. Market data is fetched once with `yfinance`, normalized into a shared feature snapshot, and then passed to both strategies. Neither strategy sees the other's output before evaluation, so disagreement is generated from design choices rather than from one agent reacting to another.

The Market Data Component is pure Python and makes no LLM call. It fetches price history and computes the derived features needed by the two strategies, including moving averages, recent returns, volume statistics, drawdown, RSI, and distance from longer-run reference points. That shared snapshot is important because it makes the comparison fair: both agents reason from the same evidence.

The two strategy agents then run as independent branches. The Momentum Trader emphasizes trend continuation, price relative to the 20-day and 50-day moving averages, and whether recent volume supports the move. The Value Contrarian emphasizes overreaction, distance from 52-week extremes, recent drawdown, and oversold conditions. Both return the same structured fields: a decision label, a confidence score, and a short numerical justification.

The Evaluator receives both structured outputs and diagnoses whether the agents agree or disagree. If the decisions match, it writes a concise consensus summary. If they diverge, it writes a disagreement analysis that identifies the actual source of divergence rather than merely restating the two labels. That distinction matters because agreement can arise for different reasons, and disagreement can emerge from different time horizons, risk tolerances, or interpretations of the same signal.

![Architecture](architecture_diagram.png)

Figure 1. Core workflow: shared market-data snapshot, independent strategy branches, evaluator routing, and optional Debate Mode.

The bonus branch, Debate Mode, is intentionally isolated from the core workflow. It only triggers after disagreement. Each strategy gets one short rebuttal turn responding to the other side, but the original decision labels remain unchanged and are preserved separately in the output. This design keeps the bonus meaningful without contaminating the required core comparison.

## Stock Selection and Rationale

I used the project's data-driven selector on the fixed candidate pool rather than choosing stocks narratively. That choice was important for two reasons. First, it reduced the temptation to hand-pick names that would make the report look cleaner after the fact. Second, it made the stock set itself part of the experiment: if the selector was sensible, it should be able to identify cases that stress different parts of the strategy logic.

The final set contained five stocks, which provided better coverage than the minimum requirement of four:

- `JNJ` was selected as the steady large-cap case because it had the strongest stability profile, with low volatility, a small price-to-moving-average gap, and limited downside shock.
- `XOM` was selected as the higher-momentum candidate because its medium-term returns and elevated volume made it the strongest momentum-style case among the remaining names.
- `TSLA` was selected as the first recent-decline case because its 30-day return of `-16.15%`, drawdown of `29.93%`, and low RSI created a natural disagreement test.
- `PFE` was selected as the sideways / low-direction case because its recent returns were modest and its moving-average spread was tight, creating a low-conviction environment.
- `NKE` was added as a fifth stock because it was the strongest remaining extreme decline candidate and provided a second, even sharper disagreement example than `TSLA`.

This was a strong stock set for the assignment because it produced both kinds of outcomes the rubric values: agreement cases and disagreement cases. `JNJ` and `PFE` tested whether the agents could remain disciplined when signals were weak. `XOM` tested whether medium-term strength would be enough to move the Momentum Trader off `HOLD`. `TSLA` and `NKE` tested whether deep drawdowns would produce genuine philosophical divergence instead of superficial wording differences.

## Results by Stock

| Ticker | Condition | Momentum Trader | Value Contrarian | Agree? | Debate Triggered? |
| --- | --- | --- | --- | --- | --- |
| JNJ | steady large-cap | HOLD (6) | HOLD (6) | Yes | No |
| XOM | high-momentum candidate | HOLD (6) | HOLD (6) | Yes | No |
| TSLA | recent decline | SELL (8) | BUY (8) | No | Yes |
| PFE | sideways / low-direction | HOLD (6) | HOLD (6) | Yes | No |
| NKE | additional recent decline | SELL (8) | BUY (8) | No | Yes |

The table already shows that the system did not collapse into trivial uniformity. The three agreement cases are all `HOLD/HOLD`, but they occur in different market contexts and for different reasons. The two disagreement cases are also structurally interesting: in both, the Momentum Trader issues `SELL` while the Value Contrarian issues `BUY`, which is the cleanest possible behavioral split for this pairing.

### JNJ: stable agreement driven by insufficient signal

`JNJ` produced the clearest steady-case agreement. The Momentum Trader saw mild positive alignment but not enough immediate strength to issue `BUY`. The report evidence indicates that recent return was weak and volume was sub-average, so momentum logic treated the stock as stable rather than compelling. The Value Contrarian also stayed neutral because the stock was only `2.92%` below its 52-week high and RSI was `59.05`, which did not look distressed or oversold enough to justify a contrarian entry.

The evaluator's consensus interpretation for `JNJ` is important: agreement did not mean identical reasoning. Momentum held because upside follow-through was not strong enough. Contrarian held because the stock did not look cheap through an overreaction lens. In other words, `JNJ` became an agreement case because both agents independently found the signal set too balanced to justify an aggressive move.

### XOM: momentum representative, but still only HOLD

`XOM` was the most surprising agreement case because the selector identified it as the momentum representative. The selector had good reasons to do so. `XOM` carried a 90-day return of `36.42%` and a volume ratio of `1.2555`, both of which are consistent with medium-term strength. Based on those metrics, I expected the Momentum Trader to be at least mildly bullish.

Instead, both strategies stayed at `HOLD`. Momentum liked the longer-horizon strength, but the current price remained below the 20-day moving average, which weakened the short-term setup enough to suppress a `BUY` label. The Value Contrarian also remained neutral because RSI sat near `48.28` and the stock was only `8.89%` below its 52-week high, so the stock did not look washed out or overreacted. The evaluator's interpretation was therefore that `XOM` looked promising on one horizon but not decisive on the horizon the strategy prompt prioritized.

This case is useful because it shows the system doing something more subtle than headline label comparison. `XOM` was not a failure of the selector or of the strategy. It was a disagreement between two definitions of momentum: medium-term relative strength in the selector versus stronger short-term trend confirmation in the agent prompt.

### TSLA: clean philosophical split on a damaged chart

`TSLA` produced the first clear disagreement case. The Momentum Trader issued `SELL (8)`, while the Value Contrarian issued `BUY (8)`. This is exactly the type of divergence the pairing was chosen to expose. `TSLA`'s recent data created a classic tension between continuation and mean reversion. On one hand, the stock had a `-16.15%` 30-day return, a `29.93%` drawdown, and price below both major moving averages. On the other hand, the same sell-off also created a low RSI that could support the argument that the market had become too pessimistic.

The Momentum Trader's reasoning was explicit and numerically grounded:

> "The current price of TSLA at 343.25 is below both the 20-day moving average of 376.26 and the 50-day moving average of 397.66, indicating a bearish trend. Additionally, the recent 30-day return is -16.15%, which shows significant deterioration in performance. The RSI is also low at 31.99, suggesting that the stock is oversold. Given these factors, the trend alignment is broken, and the price action is weak, warranting a sell decision."

The Value Contrarian read the same evidence differently. Deep drawdown and oversold conditions looked like the beginnings of a rebound setup rather than proof of a broken name. The evaluator's disagreement analysis therefore did real work here. It was not enough to say that one agent said `SELL` and the other said `BUY`; the important point was that both were responding coherently to the same data while assigning greater weight to different features. Debate Mode triggered, but neither side changed its position, which suggests that the disagreement was durable rather than superficial.

### PFE: sideways case and disciplined neutrality

`PFE` was the clearest low-direction environment in the final set. The selector identified it as the sideways case because recent returns were modest and the moving-average spread was tight. In that kind of market, both continuation logic and overreaction logic should weaken, and that is exactly what happened. The Momentum Trader issued `HOLD (6)`, and the Value Contrarian also issued `HOLD (6)`.

This is a useful case even though it is less dramatic than `TSLA` or `NKE`. A multi-agent system should not be rewarded only for producing flashy disagreement; it should also remain restrained when the feature set does not support a strong action. The evaluator's consensus summary for `PFE` is therefore analytically valuable: both agents independently concluded that the signals were not strong enough to justify an aggressive move.

`PFE` also helps interpret the other cases. Because the system can produce disciplined neutrality in a low-direction regime, the later disagreement cases look more credible. The strategies are not disagreeing simply because the prompts were written to force different answers; they agree when the evidence is genuinely ambiguous and split when the evidence activates the core tension between continuation and mean reversion.

### NKE: even sharper split than TSLA

`NKE` produced the strongest disagreement in the run. The Momentum Trader again recommended `SELL (8)`, while the Value Contrarian recommended `BUY (8)`. If `TSLA` was a clean disagreement case, `NKE` was the high-contrast version. The stock had a `-32.70%` 30-day return, a `36.37%` drawdown, an RSI of `18.89`, and it was `45.57%` below its 52-week high. Those figures simultaneously create the momentum argument for staying away and the contrarian argument for buying fear.

The Value Contrarian's justification captures that logic directly:

> "The stock NKE has experienced a significant drop, with a recent drawdown of 36.37% and a current RSI of 18.89, indicating it is oversold. Additionally, it is currently 45.57% below its 52-week high, suggesting that there is potential for recovery. The price has decreased from $64.09 to $43.13 in the last 30 days, reflecting a strong sell-off that may present a buying opportunity."

Momentum, by contrast, interpreted the same collapse as evidence that weakness was still active. The evaluator again highlighted that the disagreement came from strategic philosophy rather than inconsistent reasoning. Debate Mode did not narrow the split, which is actually a useful result: it implies that the system had surfaced a true design difference instead of a misunderstanding.

## Patterns of Agreement and Disagreement

The aggregate pattern was three agreements and two disagreements, and the pattern aligns closely with the intended behavioral differences between the strategies. Agreement appeared in `JNJ`, `XOM`, and `PFE`. Those stocks all represented moderate, balanced, or low-conviction regimes. `JNJ` was stable rather than distressed. `XOM` had some medium-term strength but weak immediate follow-through. `PFE` was mostly sideways. In each of those cases, both agents independently landed on `HOLD`, but they arrived there by different routes. Momentum generally wanted stronger short-term confirmation before issuing `BUY`, while Contrarian wanted clearer evidence of panic or oversold conditions before issuing `BUY`.

That distinction matters because it prevents a misleading interpretation of agreement. Agreement did not mean the agents had become redundant. Instead, it meant that both behavioral frameworks found the feature set insufficiently one-sided. This is exactly the kind of agreement the evaluator should recognize: convergence created by balanced evidence rather than by prompt overlap.

Disagreement appeared in `TSLA` and `NKE`, the two sharp sell-off cases. This is the heart of the project. In both stocks, the key numerical features pulled in opposite interpretive directions. Large negative 30-day returns, broken moving-average structure, and recent weakness supported the momentum `SELL`. The same drawdowns, low RSI, and greater distance from prior highs supported the contrarian `BUY`. In other words, the disagreement was not caused by noisy data or unsupported language. It was caused by the fact that trend-following and mean-reversion are different behavioral responses to the same market stress.

The debate branch adds one more layer to that interpretation. Debate Mode triggered on both disagreement cases and did not alter either final label. That is a meaningful result. If the agents had changed their minds after one short rebuttal, it might have suggested that the original disagreement was fragile. Instead, both remained loyal to their design principles. That outcome makes the disagreement easier to diagnose and strengthens the claim that the system is exposing durable strategic differences rather than rhetorical drift.

## Failure or Surprise Case

The biggest surprise was `XOM`. The stock selector marked it as the momentum representative because its 90-day return of `36.42%` and volume ratio of `1.2555` suggested stronger momentum-style behavior than the other remaining candidates. I expected that combination to produce at least a mild `BUY` from the Momentum Trader. Instead, the agent still returned `HOLD`.

This turned out to be a useful surprise rather than a hidden flaw. The selector emphasized medium-term strength, whereas the Momentum Trader prompt penalized the fact that the current price was still below the 20-day moving average. The selector and the agent were therefore looking at different momentum horizons. That mismatch is an honest limitation of the current design. In a future version, I would align the selector more closely with the prompt definition or explicitly label the selector as medium-term momentum rather than generic momentum.

## Reflection

If I had to follow one strategy for the next month with real money, I would choose the Momentum Trader. The reason is not that it is always right. The reason is that, over a one-month horizon, I value evidence that trend damage has actually started to heal before I take a position. In this run, the Value Contrarian found attractive rebound setups in `TSLA` and `NKE`, and those setups were intellectually plausible. But those were also the names with the most severe short-term damage. For a short horizon, I would rather risk missing the first part of a rebound than buy too early into a still-accelerating decline.

A useful third hybrid strategy would combine the two philosophies in sequence instead of choosing between them at the outset. It could first require a contrarian setup, such as a deep drawdown, very low RSI, or a large move away from the 52-week high. It would then wait for one momentum confirmation signal before entering, such as price reclaiming the 20-day moving average, a positive short-term return reversal, or volume-supported stabilization. That hybrid would preserve the contrarian insight that panic can create opportunity while using momentum as a timing filter to reduce the risk of catching a falling knife.

## Bonus Note

Debate Mode added value even though it did not change any final decision labels in this run. In both `TSLA` and `NKE`, the rebuttal phase showed that the disagreement was not shallow. The Momentum Trader doubled down on broken moving-average structure and large negative recent returns, while the Value Contrarian doubled down on oversold RSI and deep drawdown as evidence of overreaction. That matters because a second round can reveal whether disagreement is due to misunderstanding, weak prompting, or real strategic divergence. Here it revealed strategic divergence. The agents stayed loyal to their own philosophies after reading the opposing rationale, so the bonus branch did not create artificial convergence. Instead, it made the disagreement easier to diagnose and therefore more analytically useful.
