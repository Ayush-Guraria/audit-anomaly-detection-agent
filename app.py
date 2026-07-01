"""Audit Anomaly Detection — Streamlit analytics dashboard."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ar_automation import render_ar_tab
from src.audit_log import get_recent_logs, log_action
from src.explain import explain_transaction
from src.rag_index import build_index

# ---------------------------------------------------------------------------
# Color system — every color reference below must use these names
# ---------------------------------------------------------------------------
ACCENT         = "#00B4D8"   # teal  — clean transactions, default bars
DANGER         = "#E63946"   # red   — flagged/fraud signals, threshold lines
NEUTRAL        = "#8D99AE"   # grey  — secondary elements, gridlines, captions
TEXT_PRIMARY   = "#FFFFFF"   # white — titles and primary labels
TEXT_SECONDARY = "#ADB5BD"   # light grey — axis labels, subtitles, captions
BG_CHART       = "#1A1A2E"   # chart plot-area background
BG_PAPER       = "#16213E"   # chart paper / outer background
_GRID          = "rgba(141, 153, 174, 0.30)"  # NEUTRAL @ 30% opacity — gridlines

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
_SCORE_COLS   = ["iso_score", "xgb_score", "lr_score", "ensemble_score"]
_CHART_H      = 300
_CHART_MARGIN = dict(t=40, b=30, l=40, r=10)
_FONT         = "Inter, Arial, sans-serif"

# ---------------------------------------------------------------------------
# CSS — injected once in main(); combines metric cards + sidebar styling
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
[data-testid="stMetric"] {{
    background-color: {BG_PAPER};
    border: 1px solid {ACCENT};
    border-radius: 8px;
    padding: 16px;
}}
[data-testid="stMetric"] label {{
    color: {TEXT_SECONDARY} !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-size: 24px !important;
    font-weight: 700;
}}
[data-testid="stMetricDelta"] {{
    font-size: 11px !important;
}}
[data-testid="stSidebar"] {{
    background-color: {BG_PAPER};
    border-right: 1px solid {ACCENT};
}}
[data-testid="stSidebar"] label {{
    color: {TEXT_SECONDARY} !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
</style>
"""


# ---------------------------------------------------------------------------
# Shared chart layout factory
# ---------------------------------------------------------------------------

def make_chart_layout(title: str, xaxis_title: str = "",
                      yaxis_title: str = "", **extra) -> dict:
    """Return a Plotly layout dict with consistent professional styling.

    Keyword arguments in *extra* are merged last, enabling per-chart
    overrides (e.g. barmode, showlegend, yaxis nested keys).
    """
    layout: dict = dict(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(family=_FONT, size=14, color=TEXT_PRIMARY),
            x=0,
        ),
        xaxis=dict(
            title=dict(text=xaxis_title,
                       font=dict(family=_FONT, size=11, color=TEXT_SECONDARY)),
            tickfont=dict(family=_FONT, size=10, color=TEXT_SECONDARY),
            gridcolor=_GRID, gridwidth=1, showgrid=True,
        ),
        yaxis=dict(
            title=dict(text=yaxis_title,
                       font=dict(family=_FONT, size=11, color=TEXT_SECONDARY)),
            tickfont=dict(family=_FONT, size=10, color=TEXT_SECONDARY),
            gridcolor=_GRID, gridwidth=1, showgrid=True,
        ),
        plot_bgcolor=BG_CHART,
        paper_bgcolor=BG_PAPER,
        font=dict(family=_FONT, color=TEXT_PRIMARY),
        height=_CHART_H,
        margin=_CHART_MARGIN,
    )
    layout.update(extra)
    return layout


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

@st.cache_resource
def _init_rag_index() -> None:
    """Build the ChromaDB policy index once per process lifetime.

    Runs exactly once on cold start; skipped on every subsequent Streamlit
    rerun.  On Streamlit Community Cloud the filesystem is ephemeral, so
    every cold start triggers a fresh build from the committed policy docs.
    """
    build_index()


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """Load scored_transactions.parquet and derive TransactionHour if possible."""
    path = Path(__file__).parent / "data" / "scored_transactions.parquet"
    df = pd.read_parquet(path)
    if "TransactionDT" in df.columns:
        df["TransactionHour"] = (df["TransactionDT"] % 86400) // 3600
    return df


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_session_state(full_df: pd.DataFrame) -> None:
    """Initialise all session-state keys on first load."""
    defaults: dict = {
        "current_role": "Reviewer",
        "selected_transaction_id": None,
        "click_filter_product": None,
        "click_filter_domain": None,
        "explanation_cache": {},
        # widget keys — written by "Clear All Filters" to reset controls
        "score_threshold": 0.6,
        "product_filter": sorted(full_df["ProductCD"].dropna().unique().tolist()),
        "card_filter": sorted(full_df["card4"].dropna().unique().tolist()),
        "_product_select": "All",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Filter callbacks — defined at module level so Streamlit can reference them
# ---------------------------------------------------------------------------

def _on_product_select() -> None:
    """Sync the product selectbox widget state into click_filter_product."""
    val = st.session_state.get("_product_select", "All")
    st.session_state.click_filter_product = None if val == "All" else val


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar(full_df: pd.DataFrame) -> dict:
    """Render sidebar controls and return the current filter dict."""
    with st.sidebar:
        st.header("Filters")

        all_products = sorted(full_df["ProductCD"].dropna().unique().tolist())
        all_cards    = sorted(full_df["card4"].dropna().unique().tolist())

        prev_role = st.session_state.current_role
        role = st.selectbox("Role", ["Reviewer", "Senior Auditor"],
                            index=["Reviewer", "Senior Auditor"].index(prev_role))
        if role != prev_role:
            st.session_state.current_role = role
            log_action(role, "role_switch", details={"from": prev_role, "to": role})

        st.divider()

        threshold = st.slider("Min Ensemble Score", 0.0, 1.0,
                              step=0.05, key="score_threshold")
        products = st.multiselect("Product Category", all_products,
                                  key="product_filter")
        cards    = st.multiselect("Card Type", all_cards, key="card_filter")

        st.divider()

        if st.button("Clear All Filters", use_container_width=True):
            st.session_state.update({
                "score_threshold": 0.0,
                "product_filter": all_products,
                "card_filter": all_cards,
                "click_filter_product": None,
                "click_filter_domain": None,
                "_product_select": "All",
            })
            st.rerun()

        active = sum([
            threshold > 0.0,
            set(products) != set(all_products),
            set(cards)    != set(all_cards),
            st.session_state.click_filter_product is not None,
            st.session_state.click_filter_domain  is not None,
        ])
        if active:
            st.info(f"{active} filter{'s' if active != 1 else ''} active")

    return {"threshold": threshold, "products": products,
            "cards": cards, "role": role}


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _apply_filters(full_df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply sidebar + click-state filters and return the filtered DataFrame."""
    df = full_df[full_df["ensemble_score"] >= filters["threshold"]]

    click_prod = st.session_state.click_filter_product
    if click_prod and click_prod in filters["products"]:
        df = df[df["ProductCD"] == click_prod]
    elif filters["products"]:
        df = df[df["ProductCD"].isin(filters["products"])]

    if filters["cards"]:
        df = df[df["card4"].isin(filters["cards"])]

    click_domain = st.session_state.click_filter_domain
    if click_domain:
        df = df[df["P_emaildomain"] == click_domain]

    return df


# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------

def _kpi_row(filtered_df: pd.DataFrame, full_df: pd.DataFrame,
             threshold: float) -> None:
    """Render 5 KPI metric cards."""
    total    = len(full_df)
    flagged  = len(filtered_df)
    pct_of_total = flagged / total * 100 if total else 0.0

    baseline_fraud = full_df["isFraud"].mean() * 100 if total else 0.0
    filtered_fraud = filtered_df["isFraud"].mean() * 100 if flagged else 0.0

    avg_score = filtered_df["ensemble_score"].mean() if flagged else 0.0
    max_amt   = filtered_df["TransactionAmt"].max() if flagged else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("High Risk Flagged",   f"{flagged:,}",
              f"{pct_of_total:.1f}% of total")
    c2.metric("True Fraud Detected", f"{filtered_fraud:.1f}%",
              f"{filtered_fraud - baseline_fraud:+.1f}% vs baseline")
    c3.metric("Avg Ensemble Score",  f"{avg_score:.3f}")
    c4.metric("Highest Risk Amount", f"${max_amt:,.2f}")
    c5.metric("Dataset Coverage",    f"Showing {flagged:,}",
              f"of {total:,} transactions")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _chart_score_dist(col: st.delta_generator.DeltaGenerator,
                      filtered_df: pd.DataFrame, threshold: float) -> None:
    """Score distribution histogram: ACCENT below threshold, DANGER above."""
    below = filtered_df.loc[filtered_df["ensemble_score"] < threshold,
                            "ensemble_score"]
    above = filtered_df.loc[filtered_df["ensemble_score"] >= threshold,
                            "ensemble_score"]
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=below, name="Below threshold",
                               marker_color=ACCENT, opacity=0.7))
    fig.add_trace(go.Histogram(x=above, name="At/above threshold",
                               marker_color=DANGER, opacity=0.7))
    fig.add_vline(x=threshold, line_dash="dash", line_color=DANGER,
                  annotation_text=f"≥{threshold} flagged",
                  annotation_font_color=DANGER, annotation_font_size=10)
    fig.update_layout(**make_chart_layout(
        "Score Distribution", "Ensemble Score", "Transaction Count",
        barmode="overlay", showlegend=False,
    ))
    col.plotly_chart(fig, use_container_width=True)


def _chart_scatter(col: st.delta_generator.DeltaGenerator,
                   filtered_df: pd.DataFrame, threshold: float) -> None:
    """Amount vs risk score scatter: ACCENT=Clean, DANGER=Confirmed Fraud."""
    sample = (filtered_df.sample(500, random_state=42)
              if len(filtered_df) > 500 else filtered_df)
    clean = sample[sample["isFraud"] == 0]
    fraud = sample[sample["isFraud"] == 1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=clean["ensemble_score"], y=clean["TransactionAmt"],
        mode="markers", name="Clean",
        marker=dict(color=ACCENT, opacity=0.6, size=6),
        text=clean["TransactionID"].astype(str),
        hovertemplate="ID: %{text}<br>Score: %{x:.3f}<br>Amt: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=fraud["ensemble_score"], y=fraud["TransactionAmt"],
        mode="markers", name="Confirmed Fraud",
        marker=dict(color=DANGER, opacity=0.9, size=8),
        text=fraud["TransactionID"].astype(str),
        hovertemplate="ID: %{text}<br>Score: %{x:.3f}<br>Amt: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_vline(x=threshold, line_dash="dash", line_color=DANGER)

    layout = make_chart_layout(
        "Amount vs Risk Score", "Ensemble Score",
        "Transaction Amount ($, log scale)",
        showlegend=True,
    )
    layout["yaxis"]["type"] = "log"
    layout["legend"] = dict(font=dict(family=_FONT, color=TEXT_SECONDARY, size=10),
                            bgcolor="rgba(0,0,0,0)")
    fig.update_layout(**layout)
    col.plotly_chart(fig, use_container_width=True)


def _chart_product_bar(col: st.delta_generator.DeltaGenerator,
                       filtered_df: pd.DataFrame) -> None:
    """Avg risk by product: highest bar DANGER, rest ACCENT; selectbox filter."""
    agg = (filtered_df.groupby("ProductCD")["ensemble_score"]
           .mean()
           .sort_values(ascending=True)
           .reset_index())

    top_idx  = agg["ensemble_score"].idxmax() if not agg.empty else None
    selected = st.session_state.click_filter_product
    colors = [
        DANGER if (i == top_idx or agg.loc[i, "ProductCD"] == selected)
        else ACCENT
        for i in agg.index
    ]
    fig = go.Figure(go.Bar(
        x=agg["ensemble_score"], y=agg["ProductCD"],
        orientation="h", marker_color=colors,
        text=[f"{v:.3f}" for v in agg["ensemble_score"]],
        textposition="outside",
        textfont=dict(family=_FONT, color=TEXT_SECONDARY, size=10),
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(**make_chart_layout(
        "Risk by Product Category", "Avg Ensemble Score", "",
    ))
    with col:
        st.plotly_chart(fig, use_container_width=True)
        options = ["All"] + sorted(agg["ProductCD"].tolist())
        st.selectbox("Filter by product:", options,
                     key="_product_select", on_change=_on_product_select)


# ---------------------------------------------------------------------------
# Transaction table
# ---------------------------------------------------------------------------

def _transaction_table(filtered_df: pd.DataFrame, role: str) -> None:
    """Top-100 flagged transactions table with single-row selection."""
    top = (filtered_df.sort_values("ensemble_score", ascending=False)
           .head(100)
           .reset_index(drop=True))

    display = top.copy()
    display["TransactionAmt"]  = display["TransactionAmt"].map("${:,.2f}".format)
    display["ensemble_score"]  = display["ensemble_score"].map("{:.3f}".format)
    display["isFraud"]         = display["isFraud"].map({1: "Fraud", 0: "Clean"})

    show_cols = [c for c in [
        "TransactionID", "TransactionAmt", "ProductCD", "card4",
        "P_emaildomain", "TransactionHour", "ensemble_score", "isFraud",
    ] if c in display.columns]

    st.subheader(f"Flagged Transactions ({len(top):,})")
    st.caption("👆 Click any row to load a Claude-generated explanation below the table.")
    event = st.dataframe(display[show_cols], use_container_width=True,
                         height=400, on_select="rerun",
                         selection_mode="single-row", key="tx_table")

    rows = event.selection.rows if hasattr(event, "selection") else []
    if rows:
        tx_id = str(top.loc[rows[0], "TransactionID"])
        if tx_id != st.session_state.selected_transaction_id:
            st.session_state.selected_transaction_id = tx_id
            log_action(role, "transaction_selected", transaction_id=tx_id)
            st.rerun()


# ---------------------------------------------------------------------------
# Explanation panel helpers
# ---------------------------------------------------------------------------

def _show_tx_detail(row: pd.Series) -> None:
    """Two-column table of all transaction fields inside the expander."""
    non_score = [c for c in row.index if c not in _SCORE_COLS]
    detail_df = pd.DataFrame(
        {"Field": non_score, "Value": [row[c] for c in non_score]}
    )
    left, right = st.columns(2)
    half = len(detail_df) // 2
    left.dataframe(detail_df.iloc[:half],   hide_index=True, use_container_width=True)
    right.dataframe(detail_df.iloc[half:],  hide_index=True, use_container_width=True)


def _show_score_metrics(row: pd.Series) -> None:
    """Four st.metric cards for iso / xgb / lr / ensemble scores."""
    score_cols = [c for c in _SCORE_COLS if c in row.index]
    cols = st.columns(len(score_cols))
    for col, name in zip(cols, score_cols):
        col.metric(name, f"{row[name]:.4f}")


def _show_explanation_result(result: dict) -> None:
    """Render the structured explanation returned by explain_transaction()."""
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
        for i, action in enumerate(actions, 1):
            st.markdown(f"{i}. {action}")

    confidence = result.get("confidence", "low").lower()
    if confidence == "high":
        st.success("Confidence: High")
    elif confidence == "medium":
        st.warning("Confidence: Medium")
    else:
        st.error("Confidence: Low")


def _explanation_panel(full_df: pd.DataFrame, role: str) -> None:
    """Expander below the table showing transaction detail + Claude explanation."""
    tx_id = st.session_state.selected_transaction_id
    if tx_id is None:
        return

    mask = full_df["TransactionID"].astype(str) == tx_id
    if not mask.any():
        st.warning(f"Transaction {tx_id} not found.")
        return
    row = full_df[mask].iloc[0]

    with st.expander(f"Explanation for Transaction {tx_id}", expanded=True):
        _show_tx_detail(row)
        st.markdown("#### Anomaly Scores")
        _show_score_metrics(row)

        st.markdown("#### Explanation")
        cache = st.session_state.explanation_cache

        if tx_id in cache:
            st.caption("(cached — no API call)")
            _show_explanation_result(cache[tx_id])
        elif st.button("Generate Explanation", type="primary"):
            transaction = {k: v for k, v in row.items() if k not in _SCORE_COLS}
            scores = {k: float(row[k]) for k in _SCORE_COLS if k in row.index}
            with st.spinner("Asking Claude..."):
                result = explain_transaction(transaction, scores)
            cache[tx_id] = result
            log_action(role, "explanation_generated", transaction_id=tx_id,
                       details={"confidence": result.get("confidence")})
            _show_explanation_result(result)

        if st.button("Clear Selection"):
            st.session_state.selected_transaction_id = None
            st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def _tab_dashboard(full_df: pd.DataFrame) -> None:
    """Tab 1: sidebar filters, KPIs, 1x3 chart row, table, explanation."""
    filters     = _render_sidebar(full_df)
    filtered_df = _apply_filters(full_df, filters)
    threshold   = filters["threshold"]
    role        = filters["role"]

    _kpi_row(filtered_df, full_df, threshold)
    st.divider()

    c1, c2, c3 = st.columns(3)
    _chart_score_dist(c1, filtered_df, threshold)
    _chart_scatter(c2, filtered_df, threshold)
    _chart_product_bar(c3, filtered_df)

    st.divider()
    _transaction_table(filtered_df, role)
    _explanation_panel(full_df, role)


def _tab_audit_trail() -> None:
    """Tab 2: recent audit log entries, newest first."""
    if st.button("Refresh"):
        st.rerun()
    logs = get_recent_logs(50)
    if not logs:
        st.info("No audit entries yet.")
        return
    log_df = pd.DataFrame(logs)
    if "details" in log_df.columns:
        log_df["details"] = log_df["details"].apply(
            lambda v: str(v) if v is not None else ""
        )
    st.dataframe(log_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Audit Anomaly Detection",
                       layout="wide", page_icon="🔍")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title("Audit Anomaly Detection Agent")
    st.caption(
        "An ensemble ML model (Isolation Forest + XGBoost + Logistic Regression) "
        "scores every transaction for anomalies. Use the sidebar to filter by score "
        "threshold, product, or card type — then select any flagged transaction below "
        "to get a plain-English explanation powered by Claude, complete with policy "
        "references and suggested follow-up actions."
    )

    _init_rag_index()
    full_df = load_data()
    _init_session_state(full_df)

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Audit Trail", "🧾 AR Automation"])
    with tab1:
        _tab_dashboard(full_df)
    with tab2:
        _tab_audit_trail()
    with tab3:
        render_ar_tab()


if __name__ == "__main__":
    main()
