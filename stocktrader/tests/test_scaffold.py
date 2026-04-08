"""Basic scaffold checks for the repository layout."""

from pathlib import Path


def test_expected_files_exist() -> None:
    """Ensure the planned scaffold files are present."""

    root = Path(__file__).resolve().parents[1]
    expected = [
        root / "README.md",
        root / "DESIGN.md",
        root / "requirements.txt",
        root / ".env.example",
        root / "src" / "main.py",
        root / "src" / "schemas.py",
        root / "prompts" / "strategy_a.txt",
        root / "prompts" / "strategy_b.txt",
        root / "prompts" / "evaluator.txt",
    ]

    for path in expected:
        assert path.exists(), f"Missing scaffold file: {path}"
