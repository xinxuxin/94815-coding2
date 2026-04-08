"""Strategy agent boundaries for the two independent core branches."""

from __future__ import annotations

from .schemas import MarketDataPayload, StrategyDecision, StrategyName


def run_strategy_agent(
    strategy_name: StrategyName,
    payload: MarketDataPayload,
    prompt_path: str,
) -> StrategyDecision:
    """Run one strategy agent against the shared payload.

    TODO:
    - Load the strategy prompt template.
    - Build provider-agnostic LLM client invocation.
    - Parse and validate the structured response with Pydantic.
    - Ensure the agent does not read the other strategy's output.
    """

    raise NotImplementedError("Implement strategy agent execution in the next phase.")
