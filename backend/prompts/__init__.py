from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def get_prompt(name: str) -> str:
    """Load and return a prompt template by filename."""
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")

