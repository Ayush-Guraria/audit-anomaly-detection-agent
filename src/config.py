"""Central configuration loader for the Audit Anomaly Detection Agent."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    claude_model: str
    project_root: Path
    data_dir: Path
    models_dir: Path
    policies_dir: Path


def get_config() -> Config:
    """Load environment variables and return a frozen Config instance."""
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(_PROJECT_ROOT / ".env", override=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    return Config(
        anthropic_api_key=api_key,
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5"),
        project_root=_PROJECT_ROOT,
        data_dir=_PROJECT_ROOT / "data",
        models_dir=_PROJECT_ROOT / "models",
        policies_dir=_PROJECT_ROOT / "policies",
    )
