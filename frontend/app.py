from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st


DEFAULT_API_URL = "https://queuestorm-investigator-wcsy.onrender.com"
SITE_NAME = "QueueStorm Investigator"
SITE_TAGLINE = "SupportOps copilot · Digital Finance"

SAMPLE_INPUT: dict[str, Any] = {
    "ticket_id": "TKT-001",
    "complaint":"",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "campaign_context": "boishakh_bonanza_day_1",
    "transaction_history": [
        {
            "transaction_id": "TXN-9101",
            "timestamp": "2026-04-14T14:08:22Z",
            "type": "transfer",
            "amount": 5000,
            "counterparty": "+8801719876543",
            "status": "completed",
        },
        {
            "transaction_id": "TXN-9087",
            "timestamp": "2026-04-13T18:12:00Z",
            "type": "cash_in",
            "amount": 10000,
            "counterparty": "AGENT-512",
            "status": "completed",
        },
    ],
}

EMPTY_TXN = {
    "transaction_id": "",
    "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "type": "transfer",
    "amount": 0.0,
    "counterparty": "",
    "status": "completed",
}


def configure_page() -> None:
    st.set_page_config(
        page_title=SITE_NAME,
        page_icon="QS",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');

        :root {
            --brand:       #2563eb;
            --brand-dark:  #1d4ed8;
            --brand-bg:    #eff6ff;
            --brand-border:#bfdbfe;

            --green:       #16a34a;
            --green-bg:    #dcfce7;
            --green-border:#bbf7d0;

            --red:         #dc2626;
            --red-bg:      #fef2f2;
            --red-border:  #fecaca;

            --amber:       #d97706;
            --amber-bg:    #fffbeb;
            --amber-border:#fde68a;

            --purple:      #7c3aed;
            --purple-bg:   #f5f3ff;
            --purple-border:#ddd6fe;

            --ink:         #0f172a;
            --ink-2:       #1e293b;
            --ink-3:       #475569;
            --ink-4:       #94a3b8;

            --surface:     #ffffff;
            --surface-2:   #f8fafc;
            --border:      #e2e8f0;
            --border-2:    #f1f5f9;

            --shadow-sm:  0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
            --shadow-md:  0 4px 16px rgba(15,23,42,.08), 0 2px 4px rgba(15,23,42,.04);
            --shadow-lg:  0 8px 30px rgba(15,23,42,.10), 0 2px 8px rgba(15,23,42,.06);

            --radius-sm:  6px;
            --radius-md:  10px;
            --radius-lg:  14px;
            --radius-xl:  18px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 14px;
            color: var(--ink);
            -webkit-font-smoothing: antialiased;
        }

        .stApp {
            background: var(--surface-2);
        }

        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        .main > .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px !important;
        }

        /* ── Sticky navbar wrapper ── */
        .qs-sticky {
            position: sticky;
            top: 0.75rem;
            z-index: 100;
            padding-top: 0.2rem;
            padding-bottom: 0.7rem;
            background: var(--surface-2);
        }

        .qs-navbar {
            background: linear-gradient(180deg, #ffffff, #f8fafc);
            border: 1px solid rgba(37,99,235,.12);
            border-top: 3px solid rgba(37,99,235,.55);
            border-radius: var(--radius-xl);
            padding: 0.65rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            box-shadow: 0 10px 24px rgba(15,23,42,.06);
        }

        .qs-nav-left {
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }

        .qs-nav-logo {
            width: 34px;
            height: 34px;
            border-radius: var(--radius-md);
            background: var(--brand);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(37,99,235,.25);
        }

        .qs-nav-logo svg {
            width: 18px;
            height: 18px;
        }

        .qs-nav-name {
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--ink);
            line-height: 1.2;
            letter-spacing: -0.01em;
        }

        .qs-nav-tagline {
            font-size: 0.68rem;
            color: var(--ink-3);
            font-weight: 600;
        }

        .qs-nav-right {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* ── Pill system ── */
        .qs-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.22rem 0.6rem;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.01em;
            border: 1px solid transparent;
            white-space: nowrap;
        }

        .qs-pill-brand   { background: var(--brand-bg); color: var(--brand-dark); border-color: var(--brand-border); }
        .qs-pill-green   { background: var(--green-bg); color: var(--green); border-color: var(--green-border); }
        .qs-pill-red     { background: var(--red-bg); color: var(--red); border-color: var(--red-border); }
        .qs-pill-amber   { background: var(--amber-bg); color: var(--amber); border-color: var(--amber-border); }
        .qs-pill-purple  { background: var(--purple-bg); color: var(--purple); border-color: var(--purple-border); }

        .qs-status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .qs-dot-green { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.12); }
        .qs-dot-red   { background: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,.12); }

        /* ── Nav buttons row ── */
        .qs-nav-tabs {
            display: flex;
            gap: 0.3rem;
            background: rgba(255,255,255,.9);
            border: 1px solid rgba(37,99,235,.12);
            border-radius: var(--radius-lg);
            padding: 0.35rem 0.4rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow-sm);
        }

        /* ── Cards ── */
        .qs-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1rem 1.15rem;
            box-shadow: var(--shadow-sm);
            margin-bottom: 0.85rem;
        }

        .qs-card-title {
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--ink-2);
            margin: 0 0 0.7rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }

        .qs-card-title::before {
            content: '';
            display: inline-block;
            width: 3px;
            height: 13px;
            border-radius: 99px;
            background: var(--brand);
            flex-shrink: 0;
        }

        .qs-divider {
            height: 1px;
            background: var(--border);
            margin: 0.5rem 0 0.7rem;
        }

        /* ── Metric grid ── */
        .qs-metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.65rem;
            margin-bottom: 0.85rem;
        }

        .qs-metric {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 0.7rem 0.85rem;
            box-shadow: var(--shadow-sm);
        }

        .qs-metric-label {
            font-size: 0.64rem;
            font-weight: 600;
            color: var(--ink-4);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.3rem;
        }

        .qs-metric-value {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--ink);
            word-break: break-word;
        }

        /* ── Verdict strip ── */
        .qs-verdict-strip {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.65rem;
            margin-bottom: 0.85rem;
        }

        .qs-verdict-tile {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 0.7rem 0.85rem;
            box-shadow: var(--shadow-sm);
        }

        /* ── Chat bubbles ── */
        .qs-chat {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            margin: 0.5rem 0 0.85rem;
        }

        .qs-bubble {
            max-width: 86%;
            border-radius: var(--radius-lg);
            padding: 0.7rem 0.9rem;
            font-size: 0.85rem;
            line-height: 1.6;
        }

        .qs-bubble-ai {
            align-self: flex-start;
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--ink-2);
            border-bottom-left-radius: 4px;
            box-shadow: var(--shadow-sm);
        }

        .qs-bubble-label {
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--brand);
            margin-bottom: 0.25rem;
        }

        /* ── Connection bar ── */
        .qs-conn-bar {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 0.65rem 1rem;
            margin-bottom: 0.85rem;
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .qs-conn-label {
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--ink-4);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            white-space: nowrap;
        }

        .qs-conn-input {
            flex: 1;
            min-width: 0;
        }

        .qs-conn-btn {
            flex-shrink: 0;
        }

        /* ── Info banner ── */
        .qs-banner {
            display: flex;
            align-items: flex-start;
            gap: 0.55rem;
            background: var(--brand-bg);
            border: 1px solid var(--brand-border);
            border-radius: var(--radius-md);
            padding: 0.6rem 0.8rem;
            color: var(--brand-dark);
            font-size: 0.8rem;
            line-height: 1.5;
            margin-bottom: 0.85rem;
        }

        .qs-banner-icon {
            font-size: 0.95rem;
            margin-top: 0.05rem;
            flex-shrink: 0;
        }

        /* ── Reason chips ── */
        .qs-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 0.5rem;
        }

        /* ── Streamlit overrides ── */
        div[data-testid="stButton"] > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            padding: 0.4rem 1rem !important;
            transition: all 0.15s ease !important;
            letter-spacing: 0.01em !important;
            height: auto !important;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background: var(--brand) !important;
            border: 1px solid var(--brand-dark) !important;
            color: #fff !important;
            box-shadow: 0 1px 3px rgba(37,99,235,.25) !important;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: var(--brand-dark) !important;
            box-shadow: 0 4px 12px rgba(37,99,235,.3) !important;
            transform: translateY(-1px) !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            background: rgba(255,255,255,.92) !important;
            border: 1px solid rgba(37,99,235,.12) !important;
            color: var(--ink-2) !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            border-color: rgba(37,99,235,.24) !important;
            color: var(--brand-dark) !important;
            background: var(--brand-bg) !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="select"] {
            border-radius: var(--radius-sm) !important;
            border: 1px solid var(--border) !important;
            background: var(--surface) !important;
            color: var(--ink) !important;
            font-size: 0.84rem !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: var(--brand) !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
        }

        div[data-testid="stTextInput"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stSelectbox"] label {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            color: var(--ink-3) !important;
            margin-bottom: 0.15rem !important;
        }

        div[data-testid="stExpander"] summary {
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            color: var(--ink-3) !important;
        }

        div[data-testid="stSpinner"] {
            color: var(--brand) !important;
        }

        div[data-testid="stAlert"] {
            border-radius: var(--radius-md) !important;
            font-size: 0.82rem !important;
        }

        .stDataFrame, div[data-testid="stDataEditor"] {
            border-radius: var(--radius-md) !important;
            border-color: var(--border) !important;
            overflow: hidden;
        }

        .stCodeBlock {
            border-radius: var(--radius-md) !important;
        }

        .element-container p {
            color: var(--ink-2);
            font-size: 0.85rem;
            line-height: 1.6;
        }

        .stCaptionContainer {
            color: var(--ink-4) !important;
            font-size: 0.74rem !important;
        }

        /* small screen nav tabs wrap */
        @media (max-width: 640px) {
            .qs-metrics {
                grid-template-columns: repeat(2, 1fr);
            }
            .qs-verdict-strip {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def api_get(path: str, base_url: str) -> tuple[bool, Any]:
    try:
        response = requests.get(f"{base_url}{path}", timeout=6)
        if response.ok:
            return True, response.json()
        return False, {"status_code": response.status_code, "body": response.text}
    except requests.RequestException as exc:
        return False, {"error": str(exc)}


def api_post(path: str, payload: dict[str, Any], base_url: str) -> tuple[bool, Any]:
    try:
        response = requests.post(f"{base_url}{path}", json=payload, timeout=35)
        try:
            body: Any = response.json()
        except ValueError:
            body = {"body": response.text}
        if response.ok:
            return True, body
        return False, {"status_code": response.status_code, "body": body}
    except requests.RequestException as exc:
        return False, {"error": str(exc)}


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def check_health(base_url: str) -> tuple[bool, str]:
    ok, body = api_get("/health", base_url)
    if ok and isinstance(body, dict) and body.get("status") == "ok":
        return True, "ok"
    return False, "fail"


def pill(text: str, variant: str = "brand") -> str:
    return f'<span class="qs-pill qs-pill-{variant}">{text}</span>'


def verdict_pill(value: str | None) -> str:
    if not value:
        return "—"
    mapping = {
        "consistent": "green",
        "inconsistent": "red",
        "insufficient_data": "amber",
    }
    return pill(value, mapping.get(value, "brand"))


def severity_pill(value: str | None) -> str:
    if not value:
        return "—"
    mapping = {"low": "green", "medium": "amber", "high": "red", "critical": "red"}
    return pill(value, mapping.get(value, "brand"))


def render_navbar(base_url: str) -> str:
    if "qs_nav" not in st.session_state:
        st.session_state["qs_nav"] = "analyze"

    health_key = "health_at"
    now = datetime.now(timezone.utc).timestamp()
    if health_key not in st.session_state or now - st.session_state[health_key] > 15:
        ok, _ = check_health(base_url)
        st.session_state["health_ok"] = ok
        st.session_state[health_key] = now

    ok = st.session_state.get("health_ok", False)
    dot_cls = "qs-dot-green" if ok else "qs-dot-red"
    health_text = "API Connected" if ok else "API Disconnected"
    health_variant = "green" if ok else "red"

    st.markdown(
        f"""
        <div class="qs-sticky">
        <div class="qs-navbar">
            <div class="qs-nav-left">
                <div class="qs-nav-logo">
                    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="10" cy="10" r="7" stroke="white" stroke-width="1.8"/>
                      <circle cx="10" cy="10" r="3" fill="white"/>
                      <line x1="10" y1="1" x2="10" y2="4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
                      <line x1="10" y1="16" x2="10" y2="19" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
                      <line x1="1" y1="10" x2="4" y2="10" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
                      <line x1="16" y1="10" x2="19" y2="10" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
                    </svg>
                </div>
                <div>
                    <div class="qs-nav-name">{SITE_NAME}</div>
                    <div class="qs-nav-tagline">{SITE_TAGLINE}</div>
                </div>
            </div>
            <div class="qs-nav-right">
                <span class="qs-pill qs-pill-{health_variant}">
                    <span class="qs-status-dot {dot_cls}"></span>
                    {health_text}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_items = [
        ("Analyze", "analyze"),
        ("About", "about"),
    ]
    cols = st.columns(len(nav_items))
    for col, (label, key) in zip(cols, nav_items):
        is_active = st.session_state["qs_nav"] == key
        if col.button(label, key=f"nav-{key}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state["qs_nav"] = key

    st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state["qs_nav"]


def render_connection_settings(base_url: str) -> str:
    st.markdown(
        '<div class="qs-conn-bar">',
        unsafe_allow_html=True,
    )
    st.markdown('<span class="qs-conn-label">Backend</span>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        url = normalize_base_url(
            st.text_input(
                "API Base URL",
                value=base_url,
                key="api_url_input",
                label_visibility="collapsed",
                placeholder="http://127.0.0.1:8000",
            )
        )
    with c2:
        if st.button("Check Health", use_container_width=True, type="primary"):
            ok, _ = check_health(url)
            st.session_state["health_ok"] = ok
            st.session_state["health_at"] = datetime.now(timezone.utc).timestamp()
            if ok:
                st.success("Backend is healthy")
            else:
                st.error("Backend unreachable")
    st.markdown("</div>", unsafe_allow_html=True)
    return url


def render_analyze(base_url: str) -> None:
    st.markdown(
        """
        <div class="qs-chat">
            <div class="qs-bubble qs-bubble-ai">
                <div class="qs-bubble-label">AI Copilot</div>
                Enter the support ticket details below. I'll read the complaint alongside the customer's
                transaction history, identify the relevant transaction, assess the evidence, classify the case,
                and draft a safe reply for the support agent.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    payload = build_payload_from_form()

    col1, col2 = st.columns([1, 3])
    with col1:
        submitted = st.button("Analyze Ticket", type="primary", use_container_width=True)
    with col2:
        st.markdown(
            '<div class="qs-banner"><span class="qs-banner-icon">i</span>'
            '<span>Sends the ticket and transaction history to the AI engine. The response includes '
            'evidence reasoning, routing decision, and a customer-safe reply.</span></div>',
            unsafe_allow_html=True,
        )

    with st.expander("Preview request JSON", expanded=False):
        st.code(format_json(payload), language="json")

    if submitted:
        if not payload["ticket_id"] or not payload["complaint"]:
            st.error("Ticket ID and complaint text are required.")
            return
        with st.spinner("Investigating complaint, cross-referencing transactions..."):
            ok, body = api_post("/analyze-ticket", payload, base_url)
        if ok:
            st.session_state["last_response"] = body
            render_analysis_result(body)
        else:
            st.error("Backend returned an error.")
            st.code(format_json(body), language="json")
    elif st.session_state.get("last_response"):
        st.markdown(
            '<div class="qs-banner"><span class="qs-banner-icon">\u25c6</span>'
            '<span>Showing the previous analysis result.</span></div>',
            unsafe_allow_html=True,
        )
        render_analysis_result(st.session_state["last_response"])


def build_payload_from_form() -> dict[str, Any]:
    st.markdown('<div class="qs-card"><div class="qs-card-title">Ticket Details</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 1, 1])
    ticket_id = c1.text_input("Ticket ID", value=SAMPLE_INPUT["ticket_id"])
    language = c2.selectbox("Language", ["en", "bn", "mixed"], index=0)
    user_type = c3.selectbox("User Type", ["customer", "merchant", "agent", "unknown"], index=0)

    c4, c5 = st.columns([1, 1.4])
    channel = c4.selectbox(
        "Channel",
        ["in_app_chat", "call_center", "email", "merchant_portal", "field_agent"],
        index=0,
    )
    campaign_context = c5.text_input("Campaign Context", value=SAMPLE_INPUT["campaign_context"])
    complaint = st.text_area("Complaint Text", value=SAMPLE_INPUT["complaint"], height=120)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="qs-card"><div class="qs-card-title">Transaction History</div>', unsafe_allow_html=True)
    st.caption("Add the customer's recent transactions. Rows without a Transaction ID are ignored.")
    initial_rows = deepcopy(SAMPLE_INPUT["transaction_history"])
    df = pd.DataFrame(initial_rows)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "transaction_id": st.column_config.TextColumn("Transaction ID"),
            "timestamp": st.column_config.TextColumn("Timestamp", help="ISO 8601 format"),
            "type": st.column_config.SelectboxColumn(
                "Type",
                options=["transfer", "payment", "cash_in", "cash_out", "settlement", "refund"],
            ),
            "amount": st.column_config.NumberColumn("Amount (BDT)", min_value=0.0, step=100.0, format="%.2f"),
            "counterparty": st.column_config.TextColumn("Counterparty"),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["completed", "failed", "pending", "reversed"],
            ),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

    records = []
    for row in edited.fillna("").to_dict(orient="records"):
        if not row.get("transaction_id"):
            continue
        normalized = deepcopy(EMPTY_TXN)
        normalized.update(row)
        normalized["amount"] = float(normalized.get("amount") or 0)
        records.append(normalized)

    return {
        "ticket_id": ticket_id.strip(),
        "complaint": complaint.strip(),
        "language": language,
        "channel": channel,
        "user_type": user_type,
        "campaign_context": campaign_context.strip() or None,
        "transaction_history": records,
    }


def render_analysis_result(result: dict[str, Any]) -> None:
    ticket_id = result.get("ticket_id", "")
    st.markdown(
        f'<div class="qs-card"><div class="qs-card-title">Investigation Result — {ticket_id}</div>',
        unsafe_allow_html=True,
    )

    confidence_raw = result.get("confidence")
    conf_display = f"{float(confidence_raw):.0%}" if confidence_raw is not None else "—"

    st.markdown(
        f"""
        <div class="qs-metrics">
            <div class="qs-metric">
                <div class="qs-metric-label">Case Type</div>
                <div class="qs-metric-value">{result.get("case_type", "—")}</div>
            </div>
            <div class="qs-metric">
                <div class="qs-metric-label">Department</div>
                <div class="qs-metric-value">{result.get("department", "—")}</div>
            </div>
            <div class="qs-metric">
                <div class="qs-metric-label">Relevant TXN</div>
                <div class="qs-metric-value">{result.get("relevant_transaction_id") or "None"}</div>
            </div>
            <div class="qs-metric">
                <div class="qs-metric-label">Confidence</div>
                <div class="qs-metric-value">{conf_display}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    verdict = str(result.get("evidence_verdict") or "")
    severity = str(result.get("severity") or "")
    human_review = result.get("human_review_required")
    hr_pill = pill("Human Review Required", "red") if human_review else pill("No Review Needed", "green")

    st.markdown(
        f"""
        <div class="qs-verdict-strip">
            <div class="qs-verdict-tile">
                <div class="qs-metric-label">Evidence Verdict</div>
                <div style="margin-top:0.35rem;">{verdict_pill(verdict)}</div>
            </div>
            <div class="qs-verdict-tile">
                <div class="qs-metric-label">Severity</div>
                <div style="margin-top:0.35rem;">{severity_pill(severity)}</div>
            </div>
            <div class="qs-verdict-tile">
                <div class="qs-metric-label">Escalation</div>
                <div style="margin-top:0.35rem;">{hr_pill}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="qs-card">
            <div class="qs-card-title">Agent Summary</div>
            <div class="qs-chat">
                <div class="qs-bubble qs-bubble-ai">
                    <div class="qs-bubble-label">AI Analysis</div>
                    {result.get("agent_summary", "")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="qs-card"><div class="qs-card-title">Recommended Next Action</div>', unsafe_allow_html=True)
    st.text_area(
        "Recommended action",
        value=result.get("recommended_next_action", ""),
        height=100,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="qs-card"><div class="qs-card-title">Customer-Safe Reply</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="qs-banner" style="margin-bottom:0.6rem;"><span class="qs-banner-icon">\u26a0\ufe0f</span>'
        '<span>This reply has been checked against safety rules — no credential requests, '
        'no unauthorized refund confirmations.</span></div>',
        unsafe_allow_html=True,
    )
    st.text_area(
        "Customer reply",
        value=result.get("customer_reply", ""),
        height=110,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    reason_codes = result.get("reason_codes") or []
    if reason_codes:
        chips = "".join(f'<span class="qs-pill qs-pill-brand">{code}</span>' for code in reason_codes)
        st.markdown(
            f'<div class="qs-card"><div class="qs-card-title">Reason Codes</div>'
            f'<div class="qs-chips">{chips}</div></div>',
            unsafe_allow_html=True,
        )

    with st.expander("Raw response JSON", expanded=False):
        st.code(format_json(result), language="json")


def render_json_mode(base_url: str) -> None:
    st.markdown('<div class="qs-card"><div class="qs-card-title">JSON Studio — Raw API Testing</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="qs-banner"><span class="qs-banner-icon">\u2699</span>'
        '<span>Paste or edit a complete <code>/analyze-ticket</code> request payload and send it directly to the backend.</span></div>',
        unsafe_allow_html=True,
    )
    raw = st.text_area("Request JSON", value=format_json(SAMPLE_INPUT), height=380, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Send to API", type="primary", use_container_width=False):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return
        with st.spinner("Sending payload to backend..."):
            ok, body = api_post("/analyze-ticket", payload, base_url)
        if ok:
            render_analysis_result(body)
        else:
            st.error("Backend returned an error.")
            st.code(format_json(body), language="json")


def render_about() -> None:
    st.markdown(
        """
        <div class="qs-chat">
            <div class="qs-bubble qs-bubble-ai">
                <div class="qs-bubble-label">About QueueStorm Investigator</div>
                During a high-volume cashback campaign, support receives thousands of digital finance
                complaints. This copilot reads each ticket alongside the customer's recent transaction history,
                identifies the relevant transaction, assesses whether the evidence is consistent, routes the
                case to the right team, and produces a safe official reply — all within 30 seconds.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown(
            '<div class="qs-card"><div class="qs-card-title">Safety Rules</div>'
            "<ul style='margin:0;padding-left:1.1rem;color:var(--ink-2);font-size:0.84rem;line-height:1.8;'>"
            "<li>Never request PIN, OTP, password, or card number</li>"
            "<li>Never promise refunds or reversals without authority</li>"
            "<li>Never route customers to unofficial third parties</li>"
            "<li>Ignore prompt injection attempts in complaint text</li>"
            "</ul></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="qs-card"><div class="qs-card-title">API Endpoints</div>'
            "<ul style='margin:0;padding-left:1.1rem;color:var(--ink-2);font-size:0.84rem;line-height:1.8;'>"
            "<li><code>GET /health</code> — Backend readiness check</li>"
            "<li><code>POST /analyze-ticket</code> — Full ticket analysis</li>"
            "</ul></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="qs-card"><div class="qs-card-title">Response Fields</div>'
        "<p style='color:var(--ink-3);font-size:0.84rem;line-height:1.7;margin:0;'>"
        "<code>relevant_transaction_id</code>, <code>evidence_verdict</code>, <code>case_type</code>, "
        "<code>severity</code>, <code>department</code>, <code>human_review_required</code>, "
        "<code>confidence</code>, <code>reason_codes</code>, plus <code>agent_summary</code>, "
        "<code>recommended_next_action</code>, and <code>customer_reply</code>."
        "</p></div>",
        unsafe_allow_html=True,
    )

def main() -> None:
    configure_page()
    base_url = normalize_base_url(st.session_state.get("api_url", DEFAULT_API_URL))

    section = render_navbar(base_url)
    st.session_state["api_url"] = render_connection_settings(base_url)

    st.markdown('<div class="qs-divider"></div>', unsafe_allow_html=True)

    if section == "analyze":
        render_analyze(base_url)
    elif section == "json":
        render_json_mode(base_url)
    else:
        render_about()


if __name__ == "__main__":
    main()
