# Submission Checklist

This checklist maps repository artifacts to the explicit assignment requirements.

## Working Code Repository

- Source code: [src](/Users/macbook/Desktop/94815-coding-2/stocktrader/src)
- Prompt files: [prompts](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts)
- Per-stock outputs: [outputs](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs)
- README: [README.md](/Users/macbook/Desktop/94815-coding-2/stocktrader/README.md)
- Dependencies: [requirements.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/requirements.txt)

## Exactly Two Core Strategies

- Strategy A prompt: [strategy_a.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts/strategy_a.txt)
- Strategy B prompt: [strategy_b.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts/strategy_b.txt)
- Strategy execution: [strategy_agents.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/strategy_agents.py)

## Shared Input and Independent Analysis

- Shared market data context: [market_data.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/market_data.py)
- Parallel/separated workflow: [orchestration.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/orchestration.py)

## Evaluator Component

- Evaluator prompt: [evaluator.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts/evaluator.txt)
- Evaluator logic: [evaluator.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/evaluator.py)

## Bonus Extension: Debate Mode

- Debate prompts: [debate_a.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts/debate_a.txt), [debate_b.txt](/Users/macbook/Desktop/94815-coding-2/stocktrader/prompts/debate_b.txt)
- Debate logic and persistence: [evaluator.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/evaluator.py), [schemas.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/src/schemas.py)

## Required Output Files

- Per-stock JSON artifacts:
  - [JNJ.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/JNJ.json)
  - [XOM.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/XOM.json)
  - [TSLA.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/TSLA.json)
  - [PFE.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/PFE.json)
  - [NKE.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/NKE.json)
- Summary artifact: [summary.json](/Users/macbook/Desktop/94815-coding-2/stocktrader/outputs/summary.json)

## Comparative Analysis Report

- Markdown source: [report.md](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/report.md)
- PDF: [report.pdf](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/report.pdf)
- Architecture image: [architecture_diagram.png](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/architecture_diagram.png)

Required sections present in the main report:

- Strategy Selection and Rationale
- System Architecture
- Stock Selection and Rationale
- Results by Stock
- Patterns of Agreement and Disagreement
- Failure or Surprise Case
- Reflection
- Bonus Note

## AI Use Appendix

- Markdown source: [ai_use_appendix.md](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/ai_use_appendix.md)
- PDF: [ai_use_appendix.pdf](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/ai_use_appendix.pdf)

## Validation and Tests

- Unit and integration tests: [tests](/Users/macbook/Desktop/94815-coding-2/stocktrader/tests)
- Output artifact validation: [test_output_artifacts.py](/Users/macbook/Desktop/94815-coding-2/stocktrader/tests/test_output_artifacts.py)

## Responsible Use of Generative AI

- AI-use appendix: [ai_use_appendix.md](/Users/macbook/Desktop/94815-coding-2/stocktrader/report/ai_use_appendix.md)
- Final notes on live vs mocked work: [FINAL_NOTES.md](/Users/macbook/Desktop/94815-coding-2/stocktrader/FINAL_NOTES.md)
