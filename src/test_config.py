"""Smoke test: verify config loads correctly without revealing the API key."""

import pytest
from src.config import get_config


def test_config_loads():
    cfg = get_config()

    # API key shape check — never print the actual value
    assert cfg.anthropic_api_key.startswith("sk-ant-"), (
        "ANTHROPIC_API_KEY does not start with 'sk-ant-'"
    )
    assert len(cfg.anthropic_api_key) > 20, "ANTHROPIC_API_KEY looks too short"

    # Model name is non-empty
    assert cfg.claude_model, "CLAUDE_MODEL must be a non-empty string"

    # All project directories resolve to real paths
    assert cfg.project_root.exists(), f"PROJECT_ROOT not found: {cfg.project_root}"
    assert cfg.data_dir.exists(), f"DATA_DIR not found: {cfg.data_dir}"
    assert cfg.models_dir.exists(), f"MODELS_DIR not found: {cfg.models_dir}"
    assert cfg.policies_dir.exists(), f"POLICIES_DIR not found: {cfg.policies_dir}"
