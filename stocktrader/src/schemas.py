"""Pydantic schemas that lock the project's data contracts."""

from __future__ import annotations

import re
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


NUMERIC_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


Decision = Literal["BUY", "HOLD", "SELL"]
StrategyName = Literal["Momentum Trader", "Value Contrarian"]
SurgeDropSignal = Literal["surge", "drop", "neutral"]
DebateChange = Literal["narrowed", "widened", "unchanged"]


class MarketDataSummary(BaseModel):
    """Compact numeric market summary shared by both strategy agents."""

    model_config = ConfigDict(extra="forbid")

    history_rows: int = Field(..., ge=1, description="Number of daily rows available.")
    has_full_30d_window: bool
    has_full_90d_window: bool
    has_full_1y_window: bool

    current_price: float = Field(..., ge=0)
    price_30d_ago: float = Field(..., ge=0)
    pct_change_30d: float
    avg_daily_volume_30d: float = Field(..., ge=0)
    volatility_30d: float = Field(..., ge=0)
    moving_avg_20d: float = Field(..., ge=0)
    moving_avg_50d: float = Field(..., ge=0)
    daily_return_mean_30d: float
    max_single_day_drop_90d: float

    price_above_ma20: bool
    ma20_above_ma50: bool
    volume_vs_30d_avg: float = Field(..., ge=0)
    return_30d: float
    return_90d: float

    distance_from_52w_high_pct: float = Field(..., ge=0)
    distance_from_52w_low_pct: float = Field(..., ge=0)
    recent_drawdown_pct: float = Field(..., ge=0)
    RSI_14: float = Field(..., ge=0, le=100)
    surge_or_drop_signal: SurgeDropSignal


class MarketDataContext(BaseModel):
    """Validated market data context consumed by later agent nodes."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    run_date: str
    market_data_summary: MarketDataSummary


MarketDataPayload = MarketDataContext


class StrategyDecision(BaseModel):
    """Structured output contract for each core strategy agent."""

    model_config = ConfigDict(extra="forbid")

    name: StrategyName
    decision: Decision
    confidence: int = Field(..., ge=1, le=10)
    justification: str = Field(
        ..., description="Three to five sentences grounded in the supplied market data."
    )

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, value: str) -> str:
        """Require 3-5 sentences and at least two numeric facts."""

        sentences = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(value.strip()) if part.strip()]
        if len(sentences) < 3 or len(sentences) > 5:
            raise ValueError("Justification must contain 3 to 5 complete sentences.")

        numbers = NUMERIC_PATTERN.findall(value)
        if len(numbers) < 2:
            raise ValueError("Justification must mention at least two numeric facts from context.")

        return value


class EvaluatorOutput(BaseModel):
    """Structured evaluator output for either consensus or disagreement."""

    model_config = ConfigDict(extra="forbid")

    agents_agree: bool
    analysis: str = Field(
        ...,
        description="Consensus summary if the agents agree; disagreement analysis otherwise.",
    )


EvaluatorResult = EvaluatorOutput


class DebateTurn(BaseModel):
    """Structured second-round response for a debate participant."""

    model_config = ConfigDict(extra="forbid")

    name: StrategyName
    stance: Decision
    response: str = Field(
        ..., description="Short rebuttal or defense after reading the evaluator summary."
    )

    @field_validator("response")
    @classmethod
    def validate_response(cls, value: str) -> str:
        """Require a short, complete rebuttal."""

        sentences = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(value.strip()) if part.strip()]
        if len(sentences) < 2 or len(sentences) > 4:
            raise ValueError("Debate response must contain 2 to 4 complete sentences.")
        return value


class DebateResult(BaseModel):
    """Optional bonus output attached only when disagreement occurs."""

    model_config = ConfigDict(extra="forbid")

    triggered: bool = False
    strategy_a_response: Optional[DebateTurn] = None
    strategy_b_response: Optional[DebateTurn] = None
    disagreement_change: Optional[DebateChange] = None
    post_debate_summary: Optional[str] = None


class StockRunOutput(BaseModel):
    """Per-stock persisted result for grading-friendly submission."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    run_date: str
    market_data_summary: MarketDataSummary
    strategy_a: StrategyDecision
    strategy_b: StrategyDecision
    evaluator: EvaluatorOutput
    debate_mode: Optional[DebateResult] = None
    post_debate_synthesis: Optional[str] = None


class SummaryRow(BaseModel):
    """Aggregated summary entry for one analyzed stock."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    a_decision: Decision
    b_decision: Decision
    agree: bool


class SummaryOutput(BaseModel):
    """Aggregate summary persisted as outputs/summary.json."""

    model_config = ConfigDict(extra="forbid")

    strategies: list[StrategyName]
    stocks_analyzed: list[str]
    total_agreements: int
    total_disagreements: int
    results: list[SummaryRow]
