"""Audit Anomaly Detection — Streamlit app entry point."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.audit_log import get_recent_logs, log_action
from src.explain import explain_transaction
from src.rag_index import build_index

_SCORE_COLS = ["iso_score", "xgb_score", "lr_score", "ensemble_score"]
_DISPLAY_COLS = [
    "TransactionID",
    "TransactionAmt",
    "ProductCD",
    "card4",
    "card6",
    "P_emaildomain",
    "ensemble_score",
    "isFraud",
]


@st.cache_resource
def _init_rag_index() -> None:
    """Build the ChromaDB policy index once per process lifetime.

    @st.cache_resource ensures this runs exactly once on cold start and is
    skipped on every subsequent Streamlit rerun. On Streamlit Community Cloud
    the filesystem is ephemeral, so a cold start always triggers a fresh build.
    """
    build_index()


@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path(__file__).parent / "data" / "scored_transactions.parquet"
    return pd.read_parquet(path)


def _init_session_state() -> None:
    if "current_role" not in st.session_state:
        st.session_state.current_role = "Reviewer"
    if "selected_transaction_id" not in st.session_state:
        st.session_state.selected_transaction_id = None


def _role_selector() -> str:
    prev_role = st.session_state.current_role
    role = st.selectbox(
        "Role",
        ["Reviewer", "Senior Auditor"],
        index=["Reviewer", "Senior Auditor"].index(prev_role),
        key="role_select",
    )
    if role != prev_role:
        st.session_state.current_role = role
        log_action(role, "role_switch", details={"from": prev_role, "to": role})
    return role


def _tab_anomaly_review(df: pd.DataFrame, role: str) -> None:
    st.subheader("Top 100 Flagged Transactions")

    top = (
        df.sort_values("ensemble_score", ascending=False)
        .head(100)
        .reset_index(drop=True)
    )

    # Build display frame with renamed isFraud column
    display_cols = [c for c in _DISPLAY_COLS if c in top.columns]
    display_df = top[display_cols].rename(columns={"isFraud": "isFraud (ground truth)"})

    event = st.dataframe(
        display_df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tx_table",
    )

    selected_rows = event.selection.rows if hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        tx_id = str(top.loc[idx, "TransactionID"])
        if tx_id != st.session_state.selected_transaction_id:
            st.session_state.selected_transaction_id = tx_id
            log_action(role, "transaction_selected", transaction_id=tx_id)
            st.rerun()


def _tab_explanation_panel(df: pd.DataFrame, role: str) -> None:
    tx_id = st.session_state.selected_transaction_id

    if tx_id is None:
        st.info("Select a transaction in Tab 1 to view explanation.")
        return

    mask = df["TransactionID"].astype(str) == tx_id
    if not mask.any():
        st.warning(f"Transaction {tx_id} not found in dataset.")
        return

    row = df[mask].iloc[0]

    st.subheader(f"Transaction {tx_id}")

    # Full transaction detail as 2-column table
    detail_df = pd.DataFrame(
        {"Field": row.index.tolist(), "Value": row.values.tolist()}
    )
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    # Score metrics
    st.markdown("#### Anomaly Scores")
    score_cols = [c for c in _SCORE_COLS if c in row.index]
    metric_cols = st.columns(len(score_cols))
    for col, score_name in zip(metric_cols, score_cols):
        col.metric(score_name, f"{row[score_name]:.4f}")

    # Explanation
    st.markdown("#### Explanation")
    if st.button("Generate Explanation", type="primary"):
        transaction = {
            k: v for k, v in row.items() if k not in _SCORE_COLS
        }
        scores = {k: float(row[k]) for k in score_cols}

        with st.spinner("Calling Claude..."):
            result = explain_transaction(transaction, scores)

        st.markdown("**Summary**")
        st.write(result.get("explanation", ""))

        refs = result.get("policy_references", [])
        if refs:
            st.markdown("**Policy References**")
            for ref in refs:
                st.markdown(f"- {ref}")

        actions = result.get("suggested_followup_actions", [])
        if actions:
            st.markdown("**Suggested Follow-up Actions**")
            for action in actions:
                st.markdown(f"- {action}")

        confidence = result.get("confidence", "unknown")
        st.metric("Confidence", confidence.capitalize())

        log_action(
            role,
            "explanation_generated",
            transaction_id=tx_id,
            details={"confidence": confidence},
        )


def _tab_audit_trail() -> None:
    if st.button("Refresh"):
        st.rerun()

    logs = get_recent_logs(50)
    if not logs:
        st.info("No audit entries yet.")
        return

    log_df = pd.DataFrame(logs)
    # details column may contain dicts — stringify for display
    if "details" in log_df.columns:
        log_df["details"] = log_df["details"].apply(
            lambda v: str(v) if v is not None else ""
        )
    st.dataframe(log_df, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Audit Anomaly Detection", layout="wide")
    st.title("Audit Anomaly Detection Agent")

    _init_rag_index()
    _init_session_state()
    df = load_data()

    role = _role_selector()

    tab1, tab2, tab3 = st.tabs(["Anomaly Review", "Explanation Panel", "Audit Trail Log"])

    with tab1:
        _tab_anomaly_review(df, role)

    with tab2:
        _tab_explanation_panel(df, role)

    with tab3:
        _tab_audit_trail()


if __name__ == "__main__":
    main()
