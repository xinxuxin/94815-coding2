"""Tests for evaluator behavior and Debate Mode."""

from __future__ import annotations

from copy import deepcopy

from src.config import Settings
from src.evaluator import (
    evaluate_strategies,
    run_debate_round,
    should_trigger_debate,
    synthesize_post_debate,
)
from src.schemas import DebateResult, EvaluatorOutput, StrategyDecision


def _market_context() -> dict:
    """Return a valid market context fixture for evaluator tests."""

    return {
        "ticker": "TSLA",
        "run_date": "2026-04-08",
        "market_data_summary": {
            "history_rows": 252,
            "has_full_30d_window": True,
            "has_full_90d_window": True,
            "has_full_1y_window": True,
            "current_price": 100.0,
            "price_30d_ago": 110.5,
            "pct_change_30d": -9.5,
            "avg_daily_volume_30d": 1000000.0,
            "volatility_30d": 0.032,
            "moving_avg_20d": 104.0,
            "moving_avg_50d": 108.0,
            "daily_return_mean_30d": -0.31,
            "max_single_day_drop_90d": -5.2,
            "price_above_ma20": False,
            "ma20_above_ma50": False,
            "volume_vs_30d_avg": 0.9,
            "return_30d": -9.5,
            "return_90d": -14.2,
            "distance_from_52w_high_pct": 24.0,
            "distance_from_52w_low_pct": 8.0,
            "recent_drawdown_pct": 18.3,
            "RSI_14": 29.5,
            "surge_or_drop_signal": "drop",
        },
    }


def _momentum_sell() -> StrategyDecision:
    """Return a valid momentum-side SELL decision."""

    return StrategyDecision(
        name="Momentum Trader",
        decision="SELL",
        confidence=7,
        justification=(
            "The stock is trading at 100.0 while the 20-day average is 104.0. "
            "The 30-day return is -9.5% and the 90-day return is -14.2%, which shows persistent weakness. "
            "Volume is only 0.9 times the 30-day average, so there is no strong confirmation for a reversal. "
            "Momentum therefore favors SELL."
        ),
    )


def _contrarian_buy() -> StrategyDecision:
    """Return a valid contrarian BUY decision."""

    return StrategyDecision(
        name="Value Contrarian",
        decision="BUY",
        confidence=8,
        justification=(
            "The stock is 24.0% below its 52-week high and RSI is 29.5, which looks oversold. "
            "Recent drawdown is 18.3% and the 30-day return is -9.5%, suggesting fear may be overextended. "
            "Those numbers point to a possible overreaction rather than a permanent breakdown. "
            "A contrarian view therefore favors BUY."
        ),
    )


def _contrarian_hold() -> StrategyDecision:
    """Return a valid contrarian HOLD decision for agreement-path tests."""

    return StrategyDecision(
        name="Value Contrarian",
        decision="SELL",
        confidence=6,
        justification=(
            "The stock remains 24.0% below its 52-week high and RSI is 29.5. "
            "Recent drawdown is 18.3% while the 30-day return is still -9.5%, so the weakness may not be finished. "
            "Even a contrarian lens can wait when the decline is still accelerating. "
            "That keeps the stance at SELL."
        ),
    )


def test_agreement_path_returns_consensus_summary() -> None:
    """Evaluator should mark agreement and produce a consensus summary."""

    output = evaluate_strategies(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_hold(),
        settings=Settings(llm_provider="mock"),
    )

    validated = EvaluatorOutput.model_validate(output.model_dump())
    assert validated.agents_agree is True
    assert "Both strategies" in validated.analysis


def test_disagreement_path_returns_divergence_analysis() -> None:
    """Evaluator should explain why the strategies diverge."""

    output = evaluate_strategies(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_buy(),
        settings=Settings(llm_provider="mock"),
    )

    assert output.agents_agree is False
    assert "different interpretations" in output.analysis
    assert "Momentum" in output.analysis


def test_debate_only_triggers_on_disagreement() -> None:
    """Debate Mode should be gated by differing decisions."""

    assert should_trigger_debate(_momentum_sell(), _contrarian_buy()) is True
    assert should_trigger_debate(_momentum_sell(), _contrarian_hold()) is False

    skipped = run_debate_round(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_hold(),
        settings=Settings(llm_provider="mock"),
    )
    assert skipped.triggered is False
    assert skipped.strategy_a_response is None
    assert skipped.strategy_b_response is None


def test_debate_does_not_mutate_original_strategy_decisions() -> None:
    """Debate results should be stored separately from original decisions."""

    strategy_a = _momentum_sell()
    strategy_b = _contrarian_buy()
    before_a = deepcopy(strategy_a.model_dump())
    before_b = deepcopy(strategy_b.model_dump())

    debate_result = run_debate_round(
        market_data_context=_market_context(),
        strategy_a=strategy_a,
        strategy_b=strategy_b,
        settings=Settings(llm_provider="mock"),
    )

    assert debate_result.triggered is True
    assert strategy_a.model_dump() == before_a
    assert strategy_b.model_dump() == before_b
    assert debate_result.strategy_a_response is not None
    assert debate_result.strategy_b_response is not None


def test_mocked_examples_cover_agreement_and_disagreement_with_debate() -> None:
    """Mocked examples should cover both grading-relevant paths."""

    agree_output = evaluate_strategies(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_hold(),
        settings=Settings(llm_provider="mock"),
    )
    disagree_debate = run_debate_round(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_buy(),
        settings=Settings(llm_provider="mock"),
    )

    assert agree_output.agents_agree is True
    assert DebateResult.model_validate(disagree_debate.model_dump()).triggered is True
    assert disagree_debate.disagreement_change == "unchanged"
    assert disagree_debate.post_debate_summary is not None


def test_post_debate_synthesis_is_schema_friendly() -> None:
    """Post-debate synthesis should be a concise standalone string."""

    debate_result = run_debate_round(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_buy(),
        settings=Settings(llm_provider="mock"),
    )
    synthesis = synthesize_post_debate(
        market_data_context=_market_context(),
        strategy_a=_momentum_sell(),
        strategy_b=_contrarian_buy(),
        debate_result=debate_result,
    )

    assert isinstance(synthesis, str)
    assert "unchanged" in synthesis or "narrowed" in synthesis or "widened" in synthesis
