"""Evaluator logic for consensus, disagreement analysis, and Debate Mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .config import Settings, get_settings
from .schemas import (
    DebateResult,
    DebateTurn,
    EvaluatorOutput,
    MarketDataContext,
    StrategyDecision,
)
from .strategy_agents import invoke_structured_llm, load_prompt


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
DECISION_SCALE = {"SELL": 0, "HOLD": 1, "BUY": 2}


def evaluate_strategies(
    market_data_context: dict[str, Any],
    strategy_a: StrategyDecision,
    strategy_b: StrategyDecision,
    settings: Optional[Settings] = None,
) -> EvaluatorOutput:
    """Compare strategy outputs and return consensus or disagreement analysis."""

    validated_context = MarketDataContext.model_validate(market_data_context)
    prompt = load_prompt(str(PROMPTS_DIR / "evaluator.txt"))
    payload = {
        "market_data_context": validated_context.model_dump(),
        "strategy_a": strategy_a.model_dump(),
        "strategy_b": strategy_b.model_dump(),
    }
    return invoke_structured_llm(
        prompt=prompt,
        context=payload,
        schema=EvaluatorOutput,
        settings=_resolve_runtime_settings(settings),
    )


def should_trigger_debate(strategy_a: StrategyDecision, strategy_b: StrategyDecision) -> bool:
    """Return whether Debate Mode should run for this pair of strategy outputs."""

    return strategy_a.decision != strategy_b.decision


def run_debate_round(
    market_data_context: dict[str, Any],
    strategy_a: StrategyDecision,
    strategy_b: StrategyDecision,
    settings: Optional[Settings] = None,
) -> DebateResult:
    """Run one rebuttal turn per strategy after a disagreement."""

    if not should_trigger_debate(strategy_a, strategy_b):
        return DebateResult(triggered=False)

    validated_context = MarketDataContext.model_validate(market_data_context)
    runtime_settings = _resolve_runtime_settings(settings)
    evaluator_output = evaluate_strategies(
        market_data_context=validated_context.model_dump(),
        strategy_a=strategy_a,
        strategy_b=strategy_b,
        settings=runtime_settings,
    )

    strategy_a_turn = _run_single_debate_turn(
        prompt_path=PROMPTS_DIR / "debate_a.txt",
        market_data_context=validated_context.model_dump(),
        own_strategy=strategy_a,
        other_strategy=strategy_b,
        evaluator_output=evaluator_output,
        schema=DebateTurn,
        settings=runtime_settings,
    )
    strategy_b_turn = _run_single_debate_turn(
        prompt_path=PROMPTS_DIR / "debate_b.txt",
        market_data_context=validated_context.model_dump(),
        own_strategy=strategy_b,
        other_strategy=strategy_a,
        evaluator_output=evaluator_output,
        schema=DebateTurn,
        settings=runtime_settings,
    )

    post_debate_summary = synthesize_post_debate(
        market_data_context=validated_context.model_dump(),
        strategy_a=strategy_a,
        strategy_b=strategy_b,
        debate_result=DebateResult(
            triggered=True,
            strategy_a_response=strategy_a_turn,
            strategy_b_response=strategy_b_turn,
        ),
    )

    return DebateResult(
        triggered=True,
        strategy_a_response=strategy_a_turn,
        strategy_b_response=strategy_b_turn,
        disagreement_change=_measure_disagreement_change(
            strategy_a.decision,
            strategy_b.decision,
            strategy_a_turn.stance,
            strategy_b_turn.stance,
        ),
        post_debate_summary=post_debate_summary,
    )


def synthesize_post_debate(
    market_data_context: dict[str, Any],
    strategy_a: StrategyDecision,
    strategy_b: StrategyDecision,
    debate_result: DebateResult,
) -> str:
    """Summarize whether the debate narrowed, widened, or preserved disagreement."""

    validated_context = MarketDataContext.model_validate(market_data_context)
    if not debate_result.triggered or not debate_result.strategy_a_response or not debate_result.strategy_b_response:
        return "Debate Mode did not run because the original strategy decisions already agreed."

    change = _measure_disagreement_change(
        strategy_a.decision,
        strategy_b.decision,
        debate_result.strategy_a_response.stance,
        debate_result.strategy_b_response.stance,
    )
    summary = validated_context.market_data_summary

    if change == "narrowed":
        return (
            f"The debate narrowed the disagreement: the original gap between {strategy_a.decision} and "
            f"{strategy_b.decision} became smaller after each side re-engaged with the same data. "
            f"Even after revisiting the {summary.return_30d}% 30-day move and RSI of {summary.RSI_14}, "
            "the strategies still disagreed, but their positions moved closer together."
        )
    if change == "widened":
        return (
            f"The debate widened the disagreement: after re-examining the {summary.recent_drawdown_pct}% "
            f"drawdown and moving-average setup, the agents moved farther apart than their original "
            f"{strategy_a.decision} versus {strategy_b.decision} split. "
            "The rebuttals reinforced opposing philosophies rather than building overlap."
        )
    return (
        f"The debate left the disagreement unchanged: momentum and contrarian logic still interpret the "
        f"same {summary.return_30d}% 30-day move and RSI of {summary.RSI_14} in opposite ways. "
        f"Neither side moved off its original {strategy_a.decision} versus {strategy_b.decision} stance."
    )


def _run_single_debate_turn(
    prompt_path: Path,
    market_data_context: dict[str, Any],
    own_strategy: StrategyDecision,
    other_strategy: StrategyDecision,
    evaluator_output: EvaluatorOutput,
    schema: type[DebateTurn],
    settings: Settings,
) -> DebateTurn:
    """Invoke one strategy's debate rebuttal without mutating the original output."""

    prompt = load_prompt(str(prompt_path))
    payload = {
        "market_data_context": market_data_context,
        "your_original_output": own_strategy.model_dump(),
        "opposing_strategy_output": other_strategy.model_dump(),
        "evaluator_output": evaluator_output.model_dump(),
    }
    return invoke_structured_llm(
        prompt=prompt,
        context=payload,
        schema=schema,
        settings=settings,
    )


def _measure_disagreement_change(
    original_a: str,
    original_b: str,
    new_a: str,
    new_b: str,
) -> str:
    """Compare decision distance before and after Debate Mode."""

    original_distance = abs(DECISION_SCALE[original_a] - DECISION_SCALE[original_b])
    new_distance = abs(DECISION_SCALE[new_a] - DECISION_SCALE[new_b])
    if new_distance < original_distance:
        return "narrowed"
    if new_distance > original_distance:
        return "widened"
    return "unchanged"


def _resolve_runtime_settings(settings: Optional[Settings]) -> Settings:
    """Use live settings when configured, otherwise fall back to deterministic mock mode."""

    if settings is not None:
        return settings

    current = get_settings()
    if current.llm_provider == "mock" or current.has_live_credentials():
        return current
    return Settings(llm_provider="mock")
