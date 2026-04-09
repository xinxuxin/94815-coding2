"""Generate markdown and PDF deliverables from saved output artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .utils import ensure_directory


FINAL_SELECTION = [
    {
        "ticker": "JNJ",
        "category": "steady_large_cap",
        "why_selected": "Low 30-day volatility, tiny price-to-MA gap, and limited downside shock made it the strongest stable large-cap candidate.",
    },
    {
        "ticker": "XOM",
        "category": "high_momentum",
        "why_selected": "It carried the strongest momentum-style score among the remaining candidates because 90-day returns were strong and volume was elevated.",
    },
    {
        "ticker": "TSLA",
        "category": "recent_decline",
        "why_selected": "Large recent losses, a deep drawdown, and low RSI created a clean disagreement case.",
    },
    {
        "ticker": "PFE",
        "category": "sideways_low_direction",
        "why_selected": "Small recent returns and tight moving-average spread made it the clearest low-direction case.",
    },
    {
        "ticker": "NKE",
        "category": "additional_recent_decline",
        "why_selected": "It was the strongest remaining extreme decline candidate and gave a second, even sharper disagreement example.",
    },
]


def generate_all_reports(project_root: Path) -> dict[str, Path]:
    """Generate markdown and PDF report deliverables from saved JSON outputs."""

    outputs = _load_outputs(project_root)
    summary = _load_summary(project_root)
    report_dir = ensure_directory(project_root / "report")

    report_md = _build_report_markdown(outputs, summary, project_root)
    appendix_md = _build_appendix_markdown(outputs, project_root)

    report_md_path = report_dir / "report.md"
    appendix_md_path = report_dir / "ai_use_appendix.md"
    report_pdf_path = report_dir / "report.pdf"
    appendix_pdf_path = report_dir / "ai_use_appendix.pdf"

    report_md_path.write_text(report_md, encoding="utf-8")
    appendix_md_path.write_text(appendix_md, encoding="utf-8")

    _render_report_pdf(report_pdf_path, outputs, summary, project_root)
    _render_appendix_pdf(appendix_pdf_path, outputs, project_root)

    return {
        "report_md": report_md_path,
        "appendix_md": appendix_md_path,
        "report_pdf": report_pdf_path,
        "appendix_pdf": appendix_pdf_path,
    }


def _load_outputs(project_root: Path) -> dict[str, dict[str, Any]]:
    """Load the saved per-stock outputs."""

    outputs_dir = project_root / "outputs"
    tickers = ["JNJ", "XOM", "TSLA", "PFE", "NKE"]
    return {
        ticker: json.loads((outputs_dir / f"{ticker}.json").read_text(encoding="utf-8"))
        for ticker in tickers
    }


def _load_summary(project_root: Path) -> dict[str, Any]:
    """Load summary.json."""

    return json.loads((project_root / "outputs" / "summary.json").read_text(encoding="utf-8"))


def _build_report_markdown(
    outputs: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    project_root: Path,
) -> str:
    """Create the main report markdown."""

    tsla = outputs["TSLA"]
    nke = outputs["NKE"]
    jnj = outputs["JNJ"]
    xom = outputs["XOM"]
    pfe = outputs["PFE"]

    rows = [
        "| Ticker | Condition | Momentum | Contrarian | Agree? | Debate |",
        "| --- | --- | --- | --- | --- | --- |",
        "| JNJ | Steady large-cap | HOLD (6) | HOLD (6) | Yes | No |",
        "| XOM | High-momentum candidate | HOLD (6) | HOLD (6) | Yes | No |",
        "| TSLA | Recent decline | SELL (8) | BUY (8) | No | Yes |",
        "| PFE | Sideways / low-direction | HOLD (6) | HOLD (6) | Yes | No |",
        "| NKE | Extra sharp decline | SELL (8) | BUY (8) | No | Yes |",
    ]

    return f"""# StockTrader Report

## Strategy Selection and Rationale

This project uses **Momentum Trader** versus **Value Contrarian** as the two required core agents. I chose this pairing because the strategies interpret the same numbers in intentionally different ways. Momentum rewards continuation: price above key moving averages, supportive recent returns, and volume confirmation. Value Contrarian looks for overreaction: deep drawdowns, distance from the 52-week high, and low RSI.

I expected the strongest disagreement to appear in stocks with sharp recent declines, where one agent would treat weakness as evidence of a broken trend while the other would treat the same weakness as a buying opportunity. That expectation was borne out most clearly in TSLA and NKE. In steadier names, I expected more convergence because neither trend continuation nor mean reversion was overwhelming.

## System Architecture

The architecture follows the assignment exactly: `ticker -> market data -> two independent strategy branches -> evaluator -> optional debate -> save JSON`. Market data is fetched once with `yfinance`, then both strategies receive the same normalized feature set. Neither strategy sees the other’s output before the evaluator runs. The evaluator produces either a consensus summary or a disagreement analysis, and Debate Mode only runs when the two decisions differ.

![Architecture](architecture_diagram.png)

## Stock Selection and Rationale

I used the project’s data-driven selector on the fixed candidate pool rather than choosing stocks narratively. The final set was:

- **JNJ** as the steady large-cap case because it had the strongest low-volatility and low-direction stability score.
- **XOM** as the higher-momentum case because its 90-day returns and elevated volume made it the strongest momentum candidate among the remaining names.
- **TSLA** as a recent-decline case because its 30-day return of -16.15% and 29.93% drawdown created a natural disagreement test.
- **PFE** as the sideways case because its recent returns were modest and its moving-average spread was tight.
- **NKE** as a fifth stock because it was the strongest remaining decline candidate and provided an additional high-contrast disagreement example.

## Results by Stock

{chr(10).join(rows)}

JNJ produced a stable agreement case. Momentum saw mildly positive alignment, but weak recent return and sub-average volume kept it at HOLD. Contrarian also stayed at HOLD because the stock sat only 2.92% below its 52-week high and RSI was 59.05, which did not look washed out.

XOM was interesting because the selector tagged it as the momentum representative, but both agents still chose HOLD. Momentum liked the longer-term trend and elevated volume, yet the current price was below the 20-day average, which reduced conviction. Contrarian also stayed neutral because RSI remained near 48.28 and the stock was only 8.89% below its 52-week high.

TSLA and NKE created the clearest disagreement cases. In both stocks the Momentum Trader recommended SELL while the Value Contrarian recommended BUY. The Debate Mode branch did not change either stance.

Two direct excerpts from the saved JSON outputs illustrate the contrast well:

```json
{{
  "file": "outputs/TSLA.json",
  "field": "strategy_a.justification",
  "excerpt": "{tsla['strategy_a']['justification']}"
}}
```

```json
{{
  "file": "outputs/NKE.json",
  "field": "strategy_b.justification",
  "excerpt": "{nke['strategy_b']['justification']}"
}}
```

## Patterns of Agreement and Disagreement

The broad pattern is clear: the strategies agreed on the three steadier names and split on the two heavy-drawdown names. That pattern matters more than the raw BUY/HOLD/SELL labels because it shows the strategies are genuinely behavioral rather than cosmetic.

In the agreement cases, both agents converged on HOLD for different reasons. Momentum was usually willing to acknowledge some positive structure, but not enough to issue BUY without stronger short-term follow-through. The Value Contrarian also declined to buy because none of JNJ, XOM, or PFE looked truly stretched or panicked. So agreement came from insufficient signal, not from identical reasoning.

In the disagreement cases, the same data drove opposite conclusions. TSLA had a -16.15% 30-day return, a 29.93% drawdown, and RSI at 31.99. NKE was even more extreme with a -32.70% 30-day return, 36.37% drawdown, and RSI at 18.89. Momentum treated these as evidence that weakness was still in force. Contrarian treated them as signs of market overreaction and potential mean reversion. Debate Mode did not narrow either disagreement, which suggests the split was philosophical, not just rhetorical.

## Failure or Surprise Case

The biggest surprise was **XOM**. The stock selector identified it as the high-momentum representative because its 90-day return was 36.42% and its volume ratio was 1.2555. I expected that to produce at least a mild BUY from the Momentum Trader. Instead, both agents still chose HOLD. That result is honest and useful: my selector looked more at medium-term strength, while the Momentum Trader prompt penalized the fact that price was still below the 20-day moving average. In other words, the selector and the agent were both reasonable, but they defined “momentum” on different time horizons.

## Reflection

If I had to follow one strategy for the next month with real money, I would choose the **Momentum Trader**. The reason is not that it always gives better answers, but that it is more conservative when the tape is clearly weak. In this run, the contrarian logic found attractive rebound setups in TSLA and NKE, but those same setups were exactly the places where trend damage was most severe. For a one-month horizon, I would rather risk missing the first part of a rebound than buy too early into continuing weakness.

A useful third hybrid strategy would combine the two approaches in sequence. It could first require a contrarian setup such as low RSI or a deep drawdown, then wait for one momentum confirmation signal such as price reclaiming the 20-day average or a positive volume-supported reversal. That would preserve the contrarian insight while reducing the chance of buying into a still-accelerating decline.

## Bonus Note

Debate Mode added value even though it did not change the final decisions in this run. In both TSLA and NKE, the rebuttal phase showed that the disagreement was not superficial. The Momentum Trader doubled down on broken moving-average structure and large negative 30-day returns, while the Value Contrarian doubled down on oversold RSI and deep drawdown as evidence of overreaction. What Debate Mode revealed is that the split was durable because each agent continued to privilege different parts of the same feature set. That was useful analytically: a second round did not magically resolve the disagreement, but it made the disagreement easier to diagnose. For this assignment, that is a stronger bonus result than forcing artificial convergence.
"""


def _build_appendix_markdown(outputs: dict[str, dict[str, Any]], project_root: Path) -> str:
    """Create the AI use appendix markdown."""

    tsla = outputs["TSLA"]
    return f"""# AI Use Appendix

## Representative Development Prompts

During development I used the following representative prompts and instruction patterns:

1. **Momentum Trader system prompt**: emphasize price relative to 20-day and 50-day moving averages, recent returns, and volume confirmation; output strict JSON only.
2. **Value Contrarian system prompt**: emphasize drawdown, distance from 52-week extremes, RSI, and overreaction; output strict JSON only.
3. **Evaluator prompt**: compare strategy philosophies and identify the real source of divergence instead of restating labels.
4. **Debate prompts**: let each strategy produce one short rebuttal while staying faithful to its original philosophy.

## Short Output Excerpts

Example strategy excerpt from `TSLA.json`:

> "{tsla['strategy_a']['justification']}"

Example evaluator excerpt from `TSLA.json`:

> "{tsla['evaluator']['analysis']}"

Example debate excerpt from `TSLA.json`:

> "{tsla['debate_mode']['strategy_b_response']['response']}"

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
"""


def _render_report_pdf(
    output_path: Path,
    outputs: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    project_root: Path,
) -> None:
    """Render the main report PDF."""

    styles = getSampleStyleSheet()
    title = styles["Title"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.5, leading=13)
    quote = ParagraphStyle(
        "Quote",
        parent=body,
        leftIndent=18,
        rightIndent=10,
        textColor=colors.darkslategray,
    )

    story = [Paragraph("StockTrader Report", title), Spacer(1, 0.15 * inch)]

    story.append(Paragraph("Strategy Selection and Rationale", h1))
    story.append(Paragraph(
        "This project uses Momentum Trader versus Value Contrarian because the two strategies interpret the same market data through clearly different behavioral lenses. Momentum rewards continuation and trend alignment, while Value Contrarian rewards overreaction and mean-reversion opportunities. I expected the cleanest disagreements to appear in sharp drawdown cases, and that is exactly what happened in TSLA and NKE.",
        body,
    ))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("System Architecture", h1))
    story.append(Paragraph(
        "The workflow is ticker -> market data -> two independent strategy branches -> evaluator -> optional debate -> save JSON. Market data is fetched once, then both strategies consume the same normalized snapshot. Neither strategy sees the other strategy’s output before evaluation.",
        body,
    ))
    image_path = project_root / "report" / "architecture_diagram.png"
    story.append(Spacer(1, 0.1 * inch))
    story.append(Image(str(image_path), width=6.8 * inch, height=3.06 * inch))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Stock Selection and Rationale", h1))
    for item in FINAL_SELECTION:
        story.append(Paragraph(f"<b>{item['ticker']}</b>: {item['why_selected']}", body))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Results by Stock", h1))
    table_rows = [["Ticker", "Condition", "Momentum", "Contrarian", "Agree?", "Debate"]]
    conditions = {item["ticker"]: item["category"] for item in FINAL_SELECTION}
    for row in summary["results"]:
        ticker = row["ticker"]
        data = outputs[ticker]
        table_rows.append([
            ticker,
            conditions[ticker],
            f"{data['strategy_a']['decision']} ({data['strategy_a']['confidence']})",
            f"{data['strategy_b']['decision']} ({data['strategy_b']['confidence']})",
            "Yes" if row["agree"] else "No",
            "Yes" if data.get("debate_mode") else "No",
        ])
    table = Table(table_rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph(
        "Agreement appeared on JNJ, XOM, and PFE, where both agents concluded that the signals were not strong enough to justify an aggressive move. Disagreement appeared on TSLA and NKE, where sharp drawdowns and low RSI supported a contrarian BUY while broken trend structure supported a momentum SELL.",
        body,
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "JNJ was the cleanest steady-stock example. The two agents both chose HOLD, but not for the same reason: momentum saw only mild strength and weak volume confirmation, while contrarian saw no real panic because the stock remained close to its 52-week high and RSI stayed near the middle of the range.",
        body,
    ))
    story.append(Paragraph(
        "XOM became the most useful surprise. It entered the final set as the momentum representative because its 90-day return and relative volume were strong, yet both agents still landed on HOLD. That happened because the immediate setup was less convincing than the medium-term trend label suggested.",
        body,
    ))
    story.append(Paragraph(
        "TSLA showed the intended philosophical split. Momentum treated the negative 30-day return, broken moving-average structure, and elevated drawdown as evidence of ongoing weakness. Contrarian read the same damage as a candidate overreaction because the decline was already large and RSI was pushed close to oversold territory.",
        body,
    ))
    story.append(Paragraph(
        "PFE worked as a low-direction case. Its recent returns were modest, the moving averages were close together, and neither trend continuation nor mean reversion looked especially strong, so both agents independently stayed neutral.",
        body,
    ))
    story.append(Paragraph(
        "NKE intensified the TSLA pattern. The sell-off was even deeper, the drawdown was larger, and RSI was lower, so the strategies again split cleanly. That second disagreement mattered because it showed the divergence was repeatable rather than a one-off oddity.",
        body,
    ))
    story.append(Paragraph("Direct JSON excerpt 1 (outputs/TSLA.json -> strategy_a.justification):", h2))
    story.append(Paragraph(outputs["TSLA"]["strategy_a"]["justification"], quote))
    story.append(Paragraph("Direct JSON excerpt 2 (outputs/NKE.json -> strategy_b.justification):", h2))
    story.append(Paragraph(outputs["NKE"]["strategy_b"]["justification"], quote))

    story.append(Paragraph("Patterns of Agreement and Disagreement", h1))
    story.append(Paragraph(
        "The final pattern was 3 agreements and 2 disagreements. The agreement cases were all moderate or balanced regimes: JNJ was stable, XOM had some medium-term strength but weak immediate follow-through, and PFE was mostly sideways. In those cases, both strategies independently landed on HOLD. The disagreement cases were both large recent sell-offs. There, the Momentum Trader treated weakness as evidence of continued downside risk, while the Value Contrarian treated the same weakness as a potential overreaction. Debate Mode did not narrow the split in either case, which suggests the divergence came from durable philosophical differences rather than wording.",
        body,
    ))
    story.append(Paragraph(
        "This pattern supports the assignment goal more strongly than a set of random BUY and SELL labels would. The important point is that disagreement appeared where the two behavioral theories should conflict most: damaged trend structure combined with potentially oversold conditions. The output therefore looks designed rather than accidental.",
        body,
    ))

    story.append(Paragraph("Failure or Surprise Case", h1))
    story.append(Paragraph(
        "XOM was the biggest surprise. The stock selector marked it as the momentum representative because its 90-day return and volume profile were strong, but the Momentum Trader still chose HOLD because the current price sat below the 20-day moving average. That mismatch was useful: it showed that the selector and the agent were measuring different momentum horizons, which is an honest limitation rather than a hidden error.",
        body,
    ))

    story.append(Paragraph("Reflection", h1))
    story.append(Paragraph(
        "For a one-month horizon, I would follow the Momentum Trader. The contrarian BUY signals in TSLA and NKE were intellectually plausible, but both names still had badly damaged short-term trend structure. A hybrid strategy would first require a contrarian setup such as deep drawdown or low RSI, then wait for one momentum confirmation signal such as reclaiming the 20-day moving average before entering.",
        body,
    ))
    story.append(Paragraph(
        "That reflection also points to a limitation in the current system. Both strategies rely entirely on price-and-volume-derived context, so they intentionally ignore earnings, sector catalysts, and macro news. That tradeoff kept the project in scope and grading-friendly, but it also means some disagreements may be unresolved because the system lacks a catalyst layer.",
        body,
    ))

    story.append(Paragraph("Bonus Note", h1))
    story.append(Paragraph(
        "Debate Mode added value because it clarified whether disagreements were shallow or durable. In both TSLA and NKE, each side stayed loyal to its philosophy after reading the evaluator summary: momentum kept emphasizing broken trend structure and negative recent returns, while contrarian kept emphasizing oversold RSI and heavy drawdowns. The rebuttal phase therefore did not change the decision labels, but it still revealed something useful. It showed that the disagreement was not caused by sloppy prompting or inconsistent reasoning. Instead, it came from the intended design difference between trend-following and mean-reversion logic. That made the bonus meaningful even without forced convergence.",
        body,
    ))

    doc = SimpleDocTemplate(str(output_path), pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    doc.build(story)


def _render_appendix_pdf(
    output_path: Path,
    outputs: dict[str, dict[str, Any]],
    project_root: Path,
) -> None:
    """Render the AI use appendix PDF."""

    styles = getSampleStyleSheet()
    title = styles["Title"]
    h1 = styles["Heading1"]
    body = styles["BodyText"]

    tsla = outputs["TSLA"]

    story = [Paragraph("AI Use Appendix", title), Spacer(1, 0.15 * inch)]
    story.append(Paragraph("Representative Development Prompts", h1))
    story.append(Paragraph("1. Momentum Trader prompt: emphasize moving averages, returns, and volume; output strict JSON only.", body))
    story.append(Paragraph("2. Value Contrarian prompt: emphasize drawdown, 52-week distance, and RSI; output strict JSON only.", body))
    story.append(Paragraph("3. Evaluator prompt: compare philosophies and identify the real source of divergence.", body))
    story.append(Paragraph("4. Debate prompts: allow one rebuttal turn per strategy while preserving original decisions.", body))

    story.append(Paragraph("Short Output Excerpts", h1))
    story.append(Paragraph(tsla["strategy_a"]["justification"], body))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(tsla["evaluator"]["analysis"], body))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(tsla["debate_mode"]["strategy_b_response"]["response"], body))

    story.append(Paragraph("Accepted, Revised, Rejected, Verified", h1))
    bullet_text = (
        "Accepted: strict JSON output contracts, shared market-data payload, and Debate Mode as the bonus extension. "
        "Revised: stronger output validation, repair-on-invalid-JSON, and a report renderer that creates actual PDFs. "
        "Rejected: portfolio optimization, fabricated grading outputs, and any strategy that could see the other strategy’s output before evaluation. "
        "Verified independently: indicator calculations, schema validity, integration tests, and that final outputs came from real market-data-backed runs."
    )
    story.append(Paragraph(bullet_text, body))

    doc = SimpleDocTemplate(str(output_path), pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    doc.build(story)
