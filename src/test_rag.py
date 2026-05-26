"""Smoke tests for rag_index and explain modules."""

from src.config import get_config
from src.rag_index import build_index, retrieve
from src.explain import explain_transaction


def test_build_index_creates_chroma_dir():
    build_index()
    cfg = get_config()
    assert (cfg.project_root / ".chroma_db").exists()


def test_retrieve_returns_results():
    results = retrieve("escalation procedures")
    assert len(results) >= 1
    assert "text" in results[0]
    assert "source" in results[0]


def test_explain_transaction_returns_expected_keys():
    mock_tx = {
        "TransactionAmt": 5000.00,
        "ProductCD": "W",
        "card4": "visa",
        "addr1": "299",
        "addr2": "87",
    }
    mock_scores = {
        "iso_score": 0.8200,
        "xgb_score": 0.7900,
        "lr_score": 0.7500,
        "ensemble_score": 0.7900,
    }
    result = explain_transaction(mock_tx, mock_scores)

    print("\n--- Explanation output ---")
    print(result)

    assert isinstance(result, dict)
    for key in ("explanation", "policy_references", "suggested_followup_actions", "confidence"):
        assert key in result, f"Missing key: {key}"
