"""AR Automation — invoice risk classification and RAG-grounded collections email drafting.

Self-contained Streamlit tab module. Reuses the existing Claude config, RAG
retrieval, JSON-retry logic, and SQLite audit log rather than creating new
instances of any of them; see src/explain.py, src/rag_index.py, src/audit_log.py.
"""

import json

import anthropic
import pandas as pd
import streamlit as st

from src.audit_log import log_action
from src.config import get_config
from src.explain import _parse_json, _strip_fences
from src.rag_index import retrieve

# ---------------------------------------------------------------------------
# Color constants — mirror app.py's palette. Duplicated (not imported) because
# app.py imports this module, so importing back from app at module scope would
# be a circular import.
# ---------------------------------------------------------------------------
_ACCENT  = "#00B4D8"
_DANGER  = "#E63946"
_WARNING = "#F4A261"
_SUCCESS = "#2A9D8F"
_NEUTRAL = "#8D99AE"

REQUIRED_COLUMNS = ["invoice_number", "client_name", "amount_due", "due_date", "days_overdue"]

_TIER_COLORS = {
    "Current":  _SUCCESS,
    "At Risk":  "#E9C46A",
    "Overdue":  _WARNING,
    "Critical": _DANGER,
}

_EXPECTED_EMAIL_KEYS = ("subject_line", "email_body", "tone", "cited_policy", "urgency_level")


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def _classify_risk_tier(days_overdue: int) -> str:
    """Rule-based risk tier from days overdue."""
    if days_overdue <= 30:
        return "Current"
    if days_overdue <= 60:
        return "At Risk"
    if days_overdue <= 90:
        return "Overdue"
    return "Critical"


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of missing required columns (empty if valid)."""
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def _classify_invoices(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["risk_tier"] = out["days_overdue"].astype(int).map(_classify_risk_tier)
    return out


def _style_risk_tier(df: pd.DataFrame):
    """Return a pandas Styler that color-codes the risk_tier column."""
    def _bg(val: str) -> str:
        color = _TIER_COLORS.get(val, _NEUTRAL)
        return f"background-color: {color}; color: #16213E; font-weight: 600;"
    return (df.style
            .map(_bg, subset=["risk_tier"])
            .format({"amount_due": "${:,.2f}"}))


# ---------------------------------------------------------------------------
# RAG + Claude email drafting
# ---------------------------------------------------------------------------

def _ar_query() -> str:
    return "accounts receivable payment terms follow-up policy"


def _format_chunks(chunks: list[dict]) -> str:
    parts = [
        f"[Policy Chunk {i} — {c['source']}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    ]
    return "\n\n".join(parts)


def _ar_system_message() -> str:
    return (
        "You are an AR collections assistant at a financial institution. "
        "You draft follow-up emails for overdue invoices, grounded in the internal "
        "AR payment-terms policy. Always respond with valid JSON only — no prose, "
        "no markdown code fences."
    )


def _ar_user_message(invoice: dict, chunks: list[dict]) -> str:
    inv_lines = "\n".join(f"  {k}: {v}" for k, v in invoice.items())
    policy_text = _format_chunks(chunks)
    return (
        f"Invoice details:\n{inv_lines}\n\n"
        f"Relevant AR policy excerpts:\n{policy_text}\n\n"
        "Calibrate tone to the invoice's risk_tier:\n"
        "- Current: professional and gentle payment reminder\n"
        "- At Risk: firm reminder citing payment terms and any applicable late fee\n"
        "- Overdue: urgent follow-up requesting immediate payment\n"
        "- Critical: escalation language, note that management is being CC'd\n\n"
        "Return a JSON object with exactly these keys:\n"
        '- "subject_line": short email subject line\n'
        '- "email_body": full email body text, citing the specific policy language above\n'
        '- "tone": one of "gentle", "firm", "urgent", "escalation"\n'
        '- "cited_policy": list of policy filenames/sections cited\n'
        '- "urgency_level": one of "low", "medium", "high", "critical"\n'
        "JSON only — no other text."
    )


def _call_claude(client: anthropic.Anthropic, model: str, system: str, messages: list[dict]) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=768,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def draft_followup_email(invoice: dict) -> dict:
    """Return a structured follow-up email draft for one invoice.

    Calls Claude with RAG-retrieved AR policy context, reusing the same
    JSON-parse retry loop as src.explain.explain_transaction.
    """
    cfg = get_config()
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    chunks = retrieve(_ar_query(), k=3)
    system = _ar_system_message()
    messages = [{"role": "user", "content": _ar_user_message(invoice, chunks)}]

    raw = _call_claude(client, cfg.claude_model, system, messages)
    result = _parse_json(raw)

    if result is None:
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Respond with valid JSON only."})
        raw = _call_claude(client, cfg.claude_model, system, messages)
        result = _parse_json(raw)

    if result is None:
        result = {
            "subject_line": f"Follow-up: Invoice {invoice.get('invoice_number', '')}",
            "email_body": raw,
            "tone": "firm",
            "cited_policy": [],
            "urgency_level": "medium",
        }

    return result


# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------

def _metric_row(df: pd.DataFrame) -> None:
    total_outstanding = df["amount_due"].sum()
    avg_days_overdue = df["days_overdue"].mean()
    critical_amount = df.loc[df["risk_tier"] == "Critical", "amount_due"].sum()

    tier_counts = df["risk_tier"].value_counts()
    breakdown = " | ".join(
        f"{tier}: {tier_counts.get(tier, 0)}"
        for tier in ["Current", "At Risk", "Overdue", "Critical"]
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Outstanding", f"${total_outstanding:,.2f}")
    c2.metric("Invoices by Risk Tier", f"{len(df):,}", breakdown)
    c3.metric("Average Days Overdue", f"{avg_days_overdue:.1f}")
    c4.metric("Total Critical Amount", f"${critical_amount:,.2f}")


# ---------------------------------------------------------------------------
# Email draft panel
# ---------------------------------------------------------------------------

def _show_email_draft(result: dict) -> None:
    st.markdown(f"**Subject:** {result.get('subject_line', '')}")
    st.text_area("Email Body", result.get("email_body", ""), height=220, disabled=True)

    urgency = str(result.get("urgency_level", "low")).lower()
    tone = result.get("tone", "")
    if urgency == "critical":
        st.error(f"Urgency: Critical  |  Tone: {tone}")
    elif urgency == "high":
        st.warning(f"Urgency: High  |  Tone: {tone}")
    else:
        st.success(f"Urgency: {urgency.title()}  |  Tone: {tone}")

    cited = result.get("cited_policy", [])
    if cited:
        st.markdown("**Cited Policy**")
        for ref in cited:
            st.markdown(f"- {ref}")


def _invoice_detail_panel(df: pd.DataFrame) -> None:
    inv_id = st.session_state.ar_selected_invoice
    if inv_id is None:
        return

    mask = df["invoice_number"].astype(str) == inv_id
    if not mask.any():
        st.warning(f"Invoice {inv_id} not found.")
        return
    row = df[mask].iloc[0]

    with st.expander(f"Invoice {inv_id} — {row['client_name']}", expanded=True):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Amount Due", f"${row['amount_due']:,.2f}")
        d2.metric("Days Overdue", f"{int(row['days_overdue'])}")
        d3.metric("Risk Tier", row["risk_tier"])
        d4.metric("Due Date", str(row["due_date"]))

        cache = st.session_state.ar_email_cache
        if inv_id in cache:
            st.caption("(cached — no API call)")
            _show_email_draft(cache[inv_id])
        elif st.button("Draft Follow-Up Email", type="primary", key=f"draft_{inv_id}"):
            invoice = row.to_dict()
            with st.spinner("Asking Claude..."):
                result = draft_followup_email(invoice)
            cache[inv_id] = result
            role = st.session_state.get("current_role", "AR Automation")
            log_action(
                role, "email_drafted", transaction_id=inv_id,
                details={
                    "client_name": row["client_name"],
                    "risk_tier": row["risk_tier"],
                    "subject_line": result.get("subject_line", ""),
                },
            )
            _show_email_draft(result)

        if st.button("Clear Selection", key=f"clear_{inv_id}"):
            st.session_state.ar_selected_invoice = None
            st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_ar_tab() -> None:
    """Render the full AR Automation tab body."""
    st.subheader("AR Automation")
    st.caption(
        "Upload an accounts-receivable CSV to classify invoices by overdue risk, "
        "then draft a policy-grounded follow-up email for any invoice."
    )

    for key, default in {
        "ar_df": None,
        "ar_selected_invoice": None,
        "ar_email_cache": {},
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    uploaded = st.file_uploader("Upload AR invoice CSV", type=["csv"], key="ar_uploader")
    if uploaded is not None:
        raw_df = pd.read_csv(uploaded)
        missing = _validate_columns(raw_df)
        if missing:
            st.error(f"CSV is missing required column(s): {', '.join(missing)}")
            return
        st.session_state.ar_df = _classify_invoices(raw_df)
        st.session_state.ar_email_cache = {}
        st.session_state.ar_selected_invoice = None

    df = st.session_state.ar_df
    if df is None:
        st.info("Upload a CSV to get started, or run `generate_ar_data.py` for sample data.")
        return

    st.markdown("#### Preview")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    st.divider()
    _metric_row(df)

    st.divider()
    st.markdown(f"#### Classified Invoices ({len(df):,})")
    st.caption("👆 Select a row to draft a follow-up email for that invoice.")
    event = st.dataframe(_style_risk_tier(df), use_container_width=True, height=340,
                         hide_index=True, on_select="rerun",
                         selection_mode="single-row", key="ar_table")
    rows = event.selection.rows if hasattr(event, "selection") else []
    if rows:
        inv_id = str(df.iloc[rows[0]]["invoice_number"])
        if inv_id != st.session_state.ar_selected_invoice:
            st.session_state.ar_selected_invoice = inv_id
            st.rerun()

    _invoice_detail_panel(df)

    st.divider()
    st.download_button(
        "Download Classified Invoices (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="classified_ar_invoices.csv",
        mime="text/csv",
    )
