"""Strategy-agent execution with provider abstraction and strict schema validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import Settings, get_settings
from .schemas import DebateTurn, EvaluatorOutput, MarketDataContext, StrategyDecision


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Simple protocol for structured text generation."""

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.1,
    ) -> str:
        """Return raw text content from the model."""


class OpenAICompatibleClient:
    """Adapter for Groq, OpenAI, and Ollama via an OpenAI-compatible interface."""

    def __init__(self, base_url: str, api_key: str) -> None:
        """Create the underlying OpenAI-compatible client."""

        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.1,
    ) -> str:
        """Return the first message content from a chat completion."""

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned an empty response.")
        return content


class MockLLMClient:
    """Deterministic mock client for tests and local demo without credentials."""

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.1,
    ) -> str:
        """Generate a deterministic strategy decision from the market context."""

        del model, temperature
        system_prompt = messages[0]["content"]
        context = _extract_context_from_messages(messages)

        if "evaluator for two competing stock strategy agents" in system_prompt:
            decision = _mock_evaluator_output(context)
        elif "Strategy A in Debate Mode" in system_prompt:
            decision = _mock_debate_turn_a(context)
        elif "Strategy B in Debate Mode" in system_prompt:
            decision = _mock_debate_turn_b(context)
        elif "Momentum Trader" in system_prompt:
            decision = _mock_momentum_decision(context["market_data_summary"])
        else:
            decision = _mock_value_decision(context["market_data_summary"])

        return json.dumps(decision)


def load_prompt(path: str) -> str:
    """Load a strategy prompt from disk."""

    return Path(path).read_text(encoding="utf-8")


def get_llm_client(config: Settings) -> LLMClient:
    """Return a unified LLM client for the configured provider."""

    if config.llm_provider == "mock":
        return MockLLMClient()

    if config.llm_provider in {"groq", "openai", "ollama"}:
        if config.llm_provider != "ollama" and not config.has_live_credentials():
            raise ValueError(
                f"Provider '{config.llm_provider}' is selected but credentials are missing."
            )
        return OpenAICompatibleClient(
            base_url=config.provider_base_url(),
            api_key=config.provider_api_key(),
        )

    raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")


def invoke_structured_llm(
    prompt: str,
    context: dict[str, Any],
    schema: Type[T],
    settings: Optional[Settings] = None,
) -> T:
    """Invoke the configured LLM and validate the structured response.

    If the first response is malformed JSON or fails schema validation, one repair
    attempt is made with explicit feedback describing the problem.
    """

    resolved_settings = settings or get_settings()
    client = get_llm_client(resolved_settings)
    model_name = resolved_settings.provider_model()

    messages = _build_messages(prompt=prompt, context=context, schema=schema)
    first_response = client.generate(
        messages=messages,
        model=model_name,
        temperature=resolved_settings.llm_temperature,
    )

    try:
        return _parse_structured_output(first_response, schema)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        repair_messages = list(messages)
        repair_messages.append({"role": "assistant", "content": first_response})
        repair_messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous response was invalid. "
                    f"Validation error: {exc}. "
                    "Return ONLY valid JSON that exactly matches the schema. "
                    "Do not add markdown fences, prose, or extra keys."
                ),
            }
        )
        repaired_response = client.generate(
            messages=repair_messages,
            model=model_name,
            temperature=resolved_settings.llm_temperature,
        )
        return _parse_structured_output(repaired_response, schema)


def run_momentum_agent(
    market_data_context: dict[str, Any],
    settings: Optional[Settings] = None,
) -> StrategyDecision:
    """Run the Momentum Trader on the supplied shared market context."""

    validated_context = MarketDataContext.model_validate(market_data_context)
    prompt = load_prompt(str(PROMPTS_DIR / "strategy_a.txt"))
    return invoke_structured_llm(
        prompt=prompt,
        context=validated_context.model_dump(),
        schema=StrategyDecision,
        settings=settings,
    )


def run_value_contrarian_agent(
    market_data_context: dict[str, Any],
    settings: Optional[Settings] = None,
) -> StrategyDecision:
    """Run the Value Contrarian on the supplied shared market context."""

    validated_context = MarketDataContext.model_validate(market_data_context)
    prompt = load_prompt(str(PROMPTS_DIR / "strategy_b.txt"))
    return invoke_structured_llm(
        prompt=prompt,
        context=validated_context.model_dump(),
        schema=StrategyDecision,
        settings=settings,
    )


def _build_messages(
    prompt: str,
    context: dict[str, Any],
    schema: Type[T],
) -> List[Dict[str, str]]:
    """Construct system and user messages for one structured strategy call."""

    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Use the market data context below and return only valid JSON.\n"
                f"Required schema fields: {json.dumps(_schema_field_map(schema), indent=2)}\n"
                f"Market data context: {json.dumps(context, indent=2)}"
            ),
        },
    ]


def _schema_field_map(schema: Type[T]) -> Dict[str, Any]:
    """Return a compact field map for the target Pydantic schema."""

    json_schema = schema.model_json_schema()
    properties = json_schema.get("properties", {})
    required = json_schema.get("required", [])
    return {"required": required, "properties": properties}


def _parse_structured_output(raw_text: str, schema: Type[T]) -> T:
    """Extract JSON from raw model text and validate it against the schema."""

    parsed = json.loads(_extract_json(raw_text))
    return schema.model_validate(parsed)


def _extract_json(raw_text: str) -> str:
    """Extract a JSON object from raw text, including fenced JSON when present."""

    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Response did not contain a valid JSON object.")
    return text[start : end + 1]


def _extract_context_from_messages(messages: List[Dict[str, str]]) -> dict[str, Any]:
    """Extract the market-data context from the mock prompt payload."""

    user_content = messages[1]["content"]
    marker = "Market data context: "
    index = user_content.find(marker)
    if index == -1:
        raise ValueError("Mock client could not locate market data context.")
    context_text = user_content[index + len(marker) :].strip()
    return json.loads(context_text)


def _mock_momentum_decision(summary: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic momentum-style output from context."""

    bullish = (
        summary["price_above_ma20"]
        and summary["ma20_above_ma50"]
        and summary["return_30d"] > 5.0
    )
    weak = (
        (not summary["price_above_ma20"] and summary["return_30d"] < 0)
        or summary["return_90d"] < -8.0
    )

    if bullish:
        decision = "BUY"
        confidence = 8
    elif weak:
        decision = "SELL"
        confidence = 7
    else:
        decision = "HOLD"
        confidence = 5

    justification = (
        f"The stock is trading at {summary['current_price']} with a 30-day return of "
        f"{summary['return_30d']}%. The 20-day average is {summary['moving_avg_20d']} and the "
        f"50-day average is {summary['moving_avg_50d']}, which defines the current trend setup. "
        f"Volume is running at {summary['volume_vs_30d_avg']} times the 30-day average, so the "
        "move has measurable confirmation. Momentum therefore favors "
        f"{decision} rather than a contrarian reversal call."
    )
    return {
        "name": "Momentum Trader",
        "decision": decision,
        "confidence": confidence,
        "justification": justification,
    }


def _mock_value_decision(summary: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic contrarian-style output from context."""

    oversold = (
        summary["surge_or_drop_signal"] == "drop"
        or summary["recent_drawdown_pct"] >= 15.0
        or summary["RSI_14"] <= 35.0
    )
    overheated = (
        summary["surge_or_drop_signal"] == "surge"
        or summary["distance_from_52w_high_pct"] <= 5.0
        or summary["RSI_14"] >= 70.0
    )

    if oversold and not overheated:
        decision = "BUY"
        confidence = 8
    elif overheated and not oversold:
        decision = "SELL"
        confidence = 7
    else:
        decision = "HOLD"
        confidence = 5

    justification = (
        f"The stock sits {summary['distance_from_52w_high_pct']}% below its 52-week high and "
        f"{summary['distance_from_52w_low_pct']}% above its 52-week low. Recent drawdown is "
        f"{summary['recent_drawdown_pct']}% and RSI is {summary['RSI_14']}, which helps judge "
        "whether the move reflects fear or greed. The 30-day return is "
        f"{summary['return_30d']}%, so the recent move can be interpreted as a valuation "
        f"stretch rather than simple trend continuation. A contrarian reading therefore lands on {decision}."
    )
    return {
        "name": "Value Contrarian",
        "decision": decision,
        "confidence": confidence,
        "justification": justification,
    }


def _mock_evaluator_output(context: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic evaluator output from strategy decisions."""

    strategy_a = StrategyDecision.model_validate(context["strategy_a"])
    strategy_b = StrategyDecision.model_validate(context["strategy_b"])
    summary = context["market_data_context"]["market_data_summary"]
    agree = strategy_a.decision == strategy_b.decision

    if agree:
        analysis = (
            f"Both strategies land on {strategy_a.decision} because the same price evidence stands out. "
            f"The 30-day return is {summary['return_30d']}% and the stock sits {summary['distance_from_52w_high_pct']}% below its 52-week high, so both agents can justify a similar stance from different angles. "
            "Momentum and valuation are not pulling in opposite directions strongly enough to create a split."
        )
    else:
        analysis = (
            f"The disagreement comes from different interpretations of the same numbers. "
            f"Momentum emphasizes the 30-day return of {summary['return_30d']}%, the moving-average setup, and volume ratio of {summary['volume_vs_30d_avg']}, while the contrarian view emphasizes drawdown of {summary['recent_drawdown_pct']}% and RSI of {summary['RSI_14']}. "
            "One agent treats weakness as trend continuation risk, while the other treats it as a possible overreaction."
        )

    return EvaluatorOutput(agents_agree=agree, analysis=analysis).model_dump()


def _mock_debate_turn_a(context: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic momentum rebuttal."""

    market = context["market_data_context"]["market_data_summary"]
    original = StrategyDecision.model_validate(context["your_original_output"])
    response = (
        f"My original {original.decision} stance still follows the price trend because the 30-day return is {market['return_30d']}% and price is {'above' if market['price_above_ma20'] else 'below'} the 20-day average. "
        f"The 20-day average at {market['moving_avg_20d']} versus the 50-day average at {market['moving_avg_50d']} still matters more than trying to fade the move early. "
        "Oversold readings can persist when trend structure remains weak."
    )
    return DebateTurn(
        name="Momentum Trader",
        stance=original.decision,
        response=response,
    ).model_dump()


def _mock_debate_turn_b(context: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic contrarian rebuttal."""

    market = context["market_data_context"]["market_data_summary"]
    original = StrategyDecision.model_validate(context["your_original_output"])
    response = (
        f"My original {original.decision} stance still reflects overreaction risk because drawdown is {market['recent_drawdown_pct']}% and RSI is {market['RSI_14']}. "
        f"Being {market['distance_from_52w_high_pct']}% below the 52-week high suggests sentiment may already be washed out. "
        "Trend weakness alone does not rule out a mean-reversion opportunity."
    )
    return DebateTurn(
        name="Value Contrarian",
        stance=original.decision,
        response=response,
    ).model_dump()
