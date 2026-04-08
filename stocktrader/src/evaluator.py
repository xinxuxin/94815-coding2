"""Evaluator logic for consensus, disagreement analysis, and debate mode."""

from __future__ import annotations

from .schemas import DebateResult, EvaluatorResult, StrategyDecision


def evaluate_strategies(
    strategy_a: StrategyDecision,
    strategy_b: StrategyDecision,
) -> EvaluatorResult:
    """Compare strategy outputs and return consensus or disagreement analysis.

    TODO:
    - Route based on whether the decisions match.
    - Produce a short consensus summary on agreement.
    - Produce a substantive disagreement analysis on divergence.
    """

    raise NotImplementedError("Implement evaluator behavior in the next phase.")


def run_debate_mode(
    strategy_a: StrategyDecision,
    strategy_b: StrategyDecision,
    evaluator_result: EvaluatorResult,
) -> DebateResult:
    """Run the bonus debate branch only after a disagreement is detected.

    TODO:
    - Guard this branch with evaluator_result.agents_agree == False.
    - Let each strategy respond to the disagreement context.
    - Save debate responses into the final per-stock JSON.
    """

    raise NotImplementedError("Implement Debate Mode in the next phase.")
