"""Tests for strategy prompt loading and structured strategy execution."""

from __future__ import annotations

import json

import pytest

from src.config import Settings
from src.schemas import StrategyDecision
from src.strategy_agents import (
    PROMPTS_DIR,
    invoke_structured_llm,
    load_prompt,
    run_momentum_agent,
    run_value_contrarian_agent,
)


class FakeClient:
    """Scripted fake client for deterministic response testing."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, messages, model, temperature=0.1) -> str:  # noqa: ANN001
        del messages, model, temperature
        response = self.responses[self.calls]
        self.calls += 1
        return response


class PromptAwareFakeClient:
    """Fake client that returns different outputs per strategy prompt."""

    def generate(self, messages, model, temperature=0.1) -> str:  # noqa: ANN001
        del model, temperature
        system_prompt = messages[0]["content"]
        if "Momentum Trader" in system_prompt:
            payload = {
                "name": "Momentum Trader",
                "decision": "SELL",
                "confidence": 7,
                "justification": (
                    "The stock is below the 20-day average at 100.0 versus 104.0. "
                    "The 30-day return is -9.5% and the 90-day return is -14.2%, which shows weak trend persistence. "
                    "Volume is only 0.9 times the 30-day average, so there is no strong confirmation for a rebound. "
                    "Momentum therefore favors SELL."
                ),
            }
        else:
            payload = {
                "name": "Value Contrarian",
                "decision": "BUY",
                "confidence": 8,
                "justification": (
                    "The stock is 24.0% below its 52-week high and RSI is 29.5, which points to oversold conditions. "
                    "Recent drawdown is 18.3% and the 30-day return is -9.5%, suggesting fear may be overextended. "
                    "Even though price action is weak, those numbers support a buy-the-dip interpretation. "
                    "A contrarian view therefore favors BUY."
                ),
            }
        return json.dumps(payload)


@pytest.fixture
def sample_context() -> dict:
    """Return a compact valid market-data context fixture."""

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


def test_strategy_prompts_are_loaded() -> None:
    """Prompt files should exist and contain the fixed strategy names."""

    prompt_a = load_prompt(str(PROMPTS_DIR / "strategy_a.txt"))
    prompt_b = load_prompt(str(PROMPTS_DIR / "strategy_b.txt"))

    assert "Momentum Trader" in prompt_a
    assert "Value Contrarian" in prompt_b
    assert "Return JSON only." in prompt_a
    assert "Return JSON only." in prompt_b


def test_invoke_structured_llm_validates_schema(monkeypatch, sample_context: dict) -> None:
    """Valid structured JSON should round-trip into StrategyDecision."""

    payload = json.dumps(
        {
            "name": "Momentum Trader",
            "decision": "HOLD",
            "confidence": 6,
            "justification": (
                "The stock trades at 100.0 while the 20-day average is 104.0. "
                "The 30-day return is -9.5% and the 90-day return is -14.2%, so momentum remains weak. "
                "Volume is 0.9 times the 30-day average, which does not confirm a strong reversal. "
                "That mix of numbers supports HOLD rather than aggressive buying."
            ),
        }
    )
    fake_client = FakeClient([payload])

    monkeypatch.setattr("src.strategy_agents.get_llm_client", lambda config: fake_client)

    result = invoke_structured_llm(
        prompt="Momentum Trader",
        context=sample_context,
        schema=StrategyDecision,
        settings=Settings(llm_provider="mock"),
    )

    assert result.name == "Momentum Trader"
    assert result.confidence == 6


def test_invoke_structured_llm_uses_repair_path(monkeypatch, sample_context: dict) -> None:
    """Malformed output should trigger one repair attempt."""

    valid = json.dumps(
        {
            "name": "Value Contrarian",
            "decision": "BUY",
            "confidence": 8,
            "justification": (
                "The stock is 24.0% below its 52-week high and RSI is 29.5. "
                "Recent drawdown is 18.3% and the 30-day return is -9.5%, which points to fear-driven selling. "
                "Those values suggest the move may be an overreaction rather than a durable collapse. "
                "A contrarian reading therefore supports BUY."
            ),
        }
    )
    fake_client = FakeClient(["not-json", valid])
    monkeypatch.setattr("src.strategy_agents.get_llm_client", lambda config: fake_client)

    result = invoke_structured_llm(
        prompt="Value Contrarian",
        context=sample_context,
        schema=StrategyDecision,
        settings=Settings(llm_provider="mock"),
    )

    assert result.decision == "BUY"
    assert fake_client.calls == 2


def test_both_agents_can_disagree_on_same_context(monkeypatch, sample_context: dict) -> None:
    """Momentum and contrarian agents should stay independent on the same input."""

    monkeypatch.setattr(
        "src.strategy_agents.get_llm_client",
        lambda config: PromptAwareFakeClient(),
    )

    settings = Settings(llm_provider="mock")
    momentum = run_momentum_agent(sample_context, settings=settings)
    contrarian = run_value_contrarian_agent(sample_context, settings=settings)

    assert momentum.name == "Momentum Trader"
    assert contrarian.name == "Value Contrarian"
    assert momentum.decision != contrarian.decision
