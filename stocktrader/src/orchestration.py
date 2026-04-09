"""LangGraph orchestration for the StockTrader assignment workflow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from PIL import Image, ImageDraw

from .config import Settings, get_settings
from .evaluator import evaluate_strategies, run_debate_round
from .market_data import build_market_data_context
from .schemas import (
    DebateResult,
    StockRunOutput,
    SummaryOutput,
    SummaryRow,
)
from .stock_selector import CANDIDATE_UNIVERSE, select_representative_stocks
from .strategy_agents import run_momentum_agent, run_value_contrarian_agent
from .utils import ensure_directory, repo_root, write_json


LOGGER = logging.getLogger(__name__)


class GraphState(TypedDict, total=False):
    """State passed between LangGraph nodes."""

    ticker: str
    market_data_context: dict[str, Any]
    strategy_a: Any
    strategy_b: Any
    evaluator: Any
    debate_mode: Any
    post_debate_synthesis: str
    stock_run_output: Any
    saved_output_path: str


def build_graph(
    settings: Optional[Settings] = None,
    project_root: Optional[Path] = None,
) -> Any:
    """Construct the LangGraph workflow for one ticker run."""

    runtime_settings = _resolve_runtime_settings(settings)
    root = Path(project_root) if project_root else repo_root()
    outputs_dir = ensure_directory(root / "outputs")

    builder = StateGraph(GraphState)

    def market_data_node(state: GraphState) -> dict[str, Any]:
        ticker = state["ticker"]
        LOGGER.info("Ticker start: %s", ticker)
        context = build_market_data_context(ticker)
        LOGGER.info("Market data success: %s", ticker)
        return {"market_data_context": context}

    def strategy_a_node(state: GraphState) -> dict[str, Any]:
        result = run_momentum_agent(state["market_data_context"], settings=runtime_settings)
        LOGGER.info("Strategy A result: %s -> %s", state["ticker"], result.decision)
        return {"strategy_a": result}

    def strategy_b_node(state: GraphState) -> dict[str, Any]:
        result = run_value_contrarian_agent(state["market_data_context"], settings=runtime_settings)
        LOGGER.info("Strategy B result: %s -> %s", state["ticker"], result.decision)
        return {"strategy_b": result}

    def evaluator_node(state: GraphState) -> dict[str, Any]:
        result = evaluate_strategies(
            market_data_context=state["market_data_context"],
            strategy_a=state["strategy_a"],
            strategy_b=state["strategy_b"],
            settings=runtime_settings,
        )
        LOGGER.info("Evaluator result: %s -> agree=%s", state["ticker"], result.agents_agree)
        return {"evaluator": result}

    def debate_node(state: GraphState) -> dict[str, Any]:
        debate_result = run_debate_round(
            market_data_context=state["market_data_context"],
            strategy_a=state["strategy_a"],
            strategy_b=state["strategy_b"],
            settings=runtime_settings,
        )
        LOGGER.info("Debate triggered: %s", state["ticker"])
        return {
            "debate_mode": debate_result,
            "post_debate_synthesis": debate_result.post_debate_summary or "",
        }

    def skip_debate_node(state: GraphState) -> dict[str, Any]:
        LOGGER.info("Debate skipped: %s", state["ticker"])
        return {
            "debate_mode": DebateResult(triggered=False),
            "post_debate_synthesis": "",
        }

    def assemble_node(state: GraphState) -> dict[str, Any]:
        market_data_context = state["market_data_context"]
        debate_mode = state.get("debate_mode")
        output = StockRunOutput(
            ticker=market_data_context["ticker"],
            run_date=market_data_context["run_date"],
            market_data_summary=market_data_context["market_data_summary"],
            strategy_a=state["strategy_a"],
            strategy_b=state["strategy_b"],
            evaluator=state["evaluator"],
            debate_mode=debate_mode if debate_mode and debate_mode.triggered else None,
            post_debate_synthesis=state.get("post_debate_synthesis") or None,
        )
        return {"stock_run_output": output}

    def save_node(state: GraphState) -> dict[str, Any]:
        output = state["stock_run_output"]
        output_path = outputs_dir / f"{output.ticker}.json"
        write_json(output_path, output.model_dump())
        LOGGER.info("JSON saved: %s", output_path)
        LOGGER.info("Ticker end: %s", output.ticker)
        return {"saved_output_path": str(output_path)}

    builder.add_node("market_data", market_data_node)
    builder.add_node("strategy_a", strategy_a_node)
    builder.add_node("strategy_b", strategy_b_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("debate", debate_node)
    builder.add_node("skip_debate", skip_debate_node)
    builder.add_node("assemble", assemble_node)
    builder.add_node("save", save_node)

    builder.add_edge(START, "market_data")
    builder.add_edge("market_data", "strategy_a")
    builder.add_edge("market_data", "strategy_b")
    builder.add_edge(["strategy_a", "strategy_b"], "evaluator")
    builder.add_conditional_edges(
        "evaluator",
        _route_after_evaluator,
        {"debate": "debate", "skip_debate": "skip_debate"},
    )
    builder.add_edge("debate", "assemble")
    builder.add_edge("skip_debate", "assemble")
    builder.add_edge("assemble", "save")
    builder.add_edge("save", END)

    return builder.compile()


def run_pipeline_for_ticker(
    ticker: str,
    settings: Optional[Settings] = None,
    project_root: Optional[Path] = None,
) -> StockRunOutput:
    """Run the full graph for one ticker and return the persisted output object."""

    graph = build_graph(settings=settings, project_root=project_root)
    final_state = graph.invoke({"ticker": ticker.upper()})
    return final_state["stock_run_output"]


def run_pipeline_for_tickers(
    tickers: List[str],
    settings: Optional[Settings] = None,
    project_root: Optional[Path] = None,
) -> SummaryOutput:
    """Run the full graph for multiple tickers and save summary.json."""

    outputs = [
        run_pipeline_for_ticker(ticker=ticker, settings=settings, project_root=project_root)
        for ticker in tickers
    ]
    summary = build_summary_output(outputs)
    root = Path(project_root) if project_root else repo_root()
    summary_path = ensure_directory(root / "outputs") / "summary.json"
    write_json(summary_path, summary.model_dump())
    LOGGER.info("JSON saved: %s", summary_path)
    return summary


def run_selected_stocks(
    settings: Optional[Settings] = None,
    candidate_pool: Optional[List[str]] = None,
    project_root: Optional[Path] = None,
) -> SummaryOutput:
    """Auto-select representative stocks and run the full pipeline on them."""

    selection_report = select_representative_stocks(candidate_pool or CANDIDATE_UNIVERSE)
    selected_tickers = [item["ticker"] for item in selection_report["selected"]]
    return run_pipeline_for_tickers(
        tickers=selected_tickers,
        settings=settings,
        project_root=project_root,
    )


def build_summary_output(outputs: List[StockRunOutput]) -> SummaryOutput:
    """Aggregate per-stock outputs into the assignment summary shape."""

    total_agreements = sum(1 for output in outputs if output.evaluator.agents_agree)
    total_disagreements = len(outputs) - total_agreements
    return SummaryOutput(
        strategies=["Momentum Trader", "Value Contrarian"],
        stocks_analyzed=[output.ticker for output in outputs],
        total_agreements=total_agreements,
        total_disagreements=total_disagreements,
        results=[
            SummaryRow(
                ticker=output.ticker,
                a_decision=output.strategy_a.decision,
                b_decision=output.strategy_b.decision,
                agree=output.evaluator.agents_agree,
            )
            for output in outputs
        ],
    )


def render_architecture_diagram(project_root: Optional[Path] = None) -> Path:
    """Generate a lightweight architecture diagram PNG for the report."""

    root = Path(project_root) if project_root else repo_root()
    report_dir = ensure_directory(root / "report")
    output_path = report_dir / "architecture_diagram.png"

    image = Image.new("RGB", (1200, 540), color="white")
    draw = ImageDraw.Draw(image)

    boxes = {
        "ticker": (40, 210, 170, 280),
        "market": (220, 210, 430, 280),
        "strategy_a": (520, 110, 770, 180),
        "strategy_b": (520, 320, 770, 390),
        "evaluator": (860, 210, 1070, 280),
        "debate": (860, 380, 1070, 450),
        "save": (1120, 210, 1180, 280),
    }
    labels = {
        "ticker": "Ticker Input",
        "market": "Market Data\n(no LLM)",
        "strategy_a": "Strategy A\nMomentum Trader",
        "strategy_b": "Strategy B\nValue Contrarian",
        "evaluator": "Evaluator\nAgree or Disagree",
        "debate": "Debate Mode\n(on disagreement only)",
        "save": "Save JSON",
    }

    for name, box in boxes.items():
        draw.rounded_rectangle(box, radius=14, outline="black", width=3, fill="#f7f7f7")
        draw.multiline_text((box[0] + 12, box[1] + 18), labels[name], fill="black", spacing=6)

    _draw_arrow(draw, (170, 245), (220, 245))
    _draw_arrow(draw, (430, 245), (520, 145))
    _draw_arrow(draw, (430, 245), (520, 355))
    _draw_arrow(draw, (770, 145), (860, 245))
    _draw_arrow(draw, (770, 355), (860, 245))
    _draw_arrow(draw, (1070, 245), (1120, 245))
    _draw_arrow(draw, (965, 280), (965, 380))
    draw.text((872, 295), "if disagree", fill="black")
    _draw_arrow(draw, (1070, 415), (1120, 245))

    image.save(output_path)
    return output_path


def _route_after_evaluator(state: GraphState) -> str:
    """Route to debate only when the evaluator reports disagreement."""

    if state["evaluator"].agents_agree:
        return "skip_debate"
    return "debate"


def _resolve_runtime_settings(settings: Optional[Settings]) -> Settings:
    """Use live settings when configured, otherwise fall back to mock mode."""

    if settings is not None:
        return settings

    current = get_settings()
    if current.llm_provider == "mock" or current.has_live_credentials():
        return current
    return Settings(llm_provider="mock")


def _draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    """Draw a simple directional arrow between two points."""

    draw.line([start, end], fill="black", width=3)
    arrow_size = 8
    draw.polygon(
        [
            end,
            (end[0] - arrow_size, end[1] - arrow_size // 2),
            (end[0] - arrow_size, end[1] + arrow_size // 2),
        ],
        fill="black",
    )
