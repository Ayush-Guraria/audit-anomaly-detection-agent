"""LLM-based explanation of flagged transactions using RAG-retrieved policy context."""

import json

import anthropic

from src.config import get_config
from src.rag_index import retrieve

_EXPECTED_KEYS = ("explanation", "policy_references", "suggested_followup_actions", "confidence")


def _build_query(transaction: dict, scores: dict) -> str:
    """Build a retrieval query phrased to match language in the policy documents."""
    amt = transaction.get("TransactionAmt", "unknown")
    product = transaction.get("ProductCD", "unknown")
    return f"fraud review {product} transaction amount {amt} escalation policy anomaly detection"


def _format_chunks(chunks: list[dict]) -> str:
    parts = [
        f"[Policy Chunk {i} — {c['source']}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    ]
    return "\n\n".join(parts)


def _system_message() -> str:
    return (
        "You are an expert audit assistant at a financial institution. "
        "You analyze flagged transactions and provide clear, actionable explanations "
        "grounded in internal policy documents. Always respond with valid JSON only — "
        "no prose, no markdown code fences."
    )


def _user_message(transaction: dict, scores: dict, chunks: list[dict]) -> str:
    tx_lines = "\n".join(f"  {k}: {v}" for k, v in transaction.items())
    score_lines = "\n".join(f"  {k}: {v:.4f}" for k, v in scores.items())
    policy_text = _format_chunks(chunks)
    return (
        f"Transaction details:\n{tx_lines}\n\n"
        f"Anomaly scores (0–1, higher = more suspicious):\n{score_lines}\n\n"
        f"Relevant policy excerpts:\n{policy_text}\n\n"
        "Return a JSON object with exactly these keys:\n"
        '- "explanation": 2-3 sentences plain English explaining why this transaction is suspicious\n'
        '- "policy_references": list of policy filenames cited\n'
        '- "suggested_followup_actions": list of 2-3 specific recommended actions\n'
        '- "confidence": one of "high", "medium", "low"\n'
        "JSON only — no other text."
    )


def _parse_json(text: str) -> dict | None:
    # Try raw first, then strip markdown code fences if present
    for candidate in (text, _strip_fences(text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def _strip_fences(text: str) -> str:
    """Remove leading ```json / ``` and trailing ``` wrappers."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.endswith("```"):
            stripped = stripped[: stripped.rfind("```")]
    return stripped.strip()


def _call_claude(
    client: anthropic.Anthropic, model: str, system: str, messages: list[dict]
) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def explain_transaction(transaction: dict, scores: dict) -> dict:
    """Return a structured explanation of a flagged transaction.

    Calls Claude with RAG-retrieved policy context. Falls back gracefully on
    JSON parse errors.
    """
    cfg = get_config()
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    query = _build_query(transaction, scores)
    chunks = retrieve(query, k=3)
    system = _system_message()
    messages = [{"role": "user", "content": _user_message(transaction, scores, chunks)}]

    raw = _call_claude(client, cfg.claude_model, system, messages)
    result = _parse_json(raw)

    if result is None:
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Respond with valid JSON only."})
        raw = _call_claude(client, cfg.claude_model, system, messages)
        result = _parse_json(raw)

    if result is None:
        result = {
            "explanation": raw,
            "policy_references": [],
            "suggested_followup_actions": [],
            "confidence": "low",
        }

    return result
