"""Pydantic schemas that lock the project's data contracts."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


Decision = Literal["BUY", "HOLD", "SELL"]
StrategyName = Literal["Momentum Trader", "Value Contrarian"]
SurgeDropSignal = Literal["surge", "drop", "neutral"]


class MarketDataSummary(BaseModel):
    """Compact numeric market summary shared by both strategy agents."""

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

    ticker: str
    run_date: str
    market_data_summary: MarketDataSummary


MarketDataPayload = MarketDataContext


class StrategyDecision(BaseModel):
    """Structured output contract for each core strategy agent."""

    name: StrategyName
    decision: Decision
    confidence: int = Field(..., ge=1, le=10)
    justification: str = Field(
        ..., description="Three to five sentences grounded in the supplied market data."
    )


class EvaluatorOutput(BaseModel):
    """Structured evaluator output for either consensus or disagreement."""

    agents_agree: bool
    analysis: str = Field(
        ...,
        description="Consensus summary if the agents agree; disagreement analysis otherwise.",
    )


EvaluatorResult = EvaluatorOutput


class DebateTurn(BaseModel):
    """Structured second-round response for a debate participant."""

    name: StrategyName
    stance: Decision
    response: str = Field(
        ..., description="Short rebuttal or defense after reading the evaluator summary."
    )


class DebateResult(BaseModel):
    """Optional bonus output attached only when disagreement occurs."""

    triggered: bool = False
    strategy_a_response: Optional[DebateTurn] = None
    strategy_b_response: Optional[DebateTurn] = None
    post_debate_summary: Optional[str] = None


class StockRunOutput(BaseModel):
    """Per-stock persisted result for grading-friendly submission."""

    ticker: str
    run_date: str
    market_data_summary: MarketDataSummary
    strategy_a: StrategyDecision
    strategy_b: StrategyDecision
    evaluator: EvaluatorOutput
    debate_mode: Optional[DebateResult] = None


class SummaryRow(BaseModel):
    """Aggregated summary entry for one analyzed stock."""

    ticker: str
    a_decision: Decision
    b_decision: Decision
    agree: bool


class SummaryOutput(BaseModel):
    """Aggregate summary persisted as outputs/summary.json."""

    strategies: list[StrategyName]
    stocks_analyzed: list[str]
    total_agreements: int
    total_disagreements: int
    results: list[SummaryRow]
