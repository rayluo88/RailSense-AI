import httpx
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

import os

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="RailSense-AI",
    page_icon="RS",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS Injection — matches the design system from shared-styles.css
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg-primary: #f8f9fb;
  --bg-secondary: #ffffff;
  --bg-card: #ffffff;
  --bg-card-hover: #f1f5f9;
  --bg-elevated: #f1f5f9;
  --border-subtle: #e2e8f0;
  --border-default: #cbd5e1;
  --text-primary: #1e293b;
  --text-secondary: #475569;
  --text-muted: #64748b;
  --text-dim: #94a3b8;
  --critical: #dc2626;
  --critical-bg: #fef2f2;
  --critical-border: #fecaca;
  --critical-glow: rgba(220, 38, 38, 0.12);
  --warning: #d97706;
  --warning-bg: #fffbeb;
  --warning-border: #fde68a;
  --healthy: #059669;
  --healthy-bg: #ecfdf5;
  --healthy-border: #a7f3d0;
  --info: #2563eb;
  --info-bg: #eff6ff;
  --info-border: #bfdbfe;
  --nsl-red: #d42e12;
  --ewl-green: #009645;
  --ccl-orange: #e88e00;
  --dtl-blue: #005ec4;
  --nel-purple: #8b5cf6;
  --tel-brown: #9d5b25;
  --accent: #2563eb;
  --accent-bg: #eff6ff;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
  --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }

/* ── Global background and font ── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    font-family: var(--font-sans) !important;
    color: var(--text-primary) !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
    box-shadow: 1px 0 3px rgba(0,0,0,0.04);
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    font-family: var(--font-sans) !important;
    color: var(--text-secondary) !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
    border-radius: var(--radius-md) !important;
    transition: all 0.15s ease;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: var(--bg-card-hover) !important;
}

/* ── Metric containers — card style with colored top border ── */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 24px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    position: relative;
    overflow: hidden;
}

[data-testid="stMetric"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: var(--text-muted) !important;
    font-family: var(--font-sans) !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    letter-spacing: -1px !important;
    line-height: 1 !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 11px !important;
    font-family: var(--font-mono) !important;
}

/* Colored top borders for metric cards via nth-child */
.metric-critical [data-testid="stMetric"] {
    border-top: 3px solid var(--critical) !important;
}
.metric-critical [data-testid="stMetricValue"] {
    color: var(--critical) !important;
}

.metric-warning [data-testid="stMetric"] {
    border-top: 3px solid var(--warning) !important;
}
.metric-warning [data-testid="stMetricValue"] {
    color: var(--warning) !important;
}

.metric-info [data-testid="stMetric"] {
    border-top: 3px solid var(--info) !important;
}
.metric-info [data-testid="stMetricValue"] {
    color: var(--info) !important;
}

.metric-healthy [data-testid="stMetric"] {
    border-top: 3px solid var(--healthy) !important;
}
.metric-healthy [data-testid="stMetricValue"] {
    color: var(--healthy) !important;
}

/* ── Severity Badges ── */
.severity-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: var(--font-mono);
}

.severity-critical {
    background: var(--critical-bg);
    color: var(--critical);
    border: 1px solid var(--critical-border);
}

.severity-warning {
    background: var(--warning-bg);
    color: var(--warning);
    border: 1px solid var(--warning-border);
}

.severity-info {
    background: var(--info-bg);
    color: var(--info);
    border: 1px solid var(--info-border);
}

.severity-healthy {
    background: var(--healthy-bg);
    color: var(--healthy);
    border: 1px solid var(--healthy-border);
}

/* ── Line Badges ── */
.line-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    height: 20px;
    border-radius: 3px;
    font-size: 9px;
    font-weight: 700;
    font-family: var(--font-mono);
    color: white;
    padding: 0 4px;
}

.line-nsl { background: var(--nsl-red); }
.line-ewl { background: var(--ewl-green); }
.line-ccl { background: var(--ccl-orange); }
.line-dtl { background: var(--dtl-blue); }
.line-nel { background: var(--nel-purple); }
.line-tel { background: var(--tel-brown); }

/* ── Alert Cards ── */
.alert-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: all 0.2s ease;
}

.alert-card:hover {
    border-color: var(--border-default);
}

.alert-card-critical {
    border-left: 3px solid var(--critical) !important;
}

.alert-card-warning {
    border-left: 3px solid var(--warning) !important;
}

.alert-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
}

.alert-pulse {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 4px;
    flex-shrink: 0;
}

.alert-pulse-critical {
    background: var(--critical);
    box-shadow: 0 0 8px var(--critical-glow);
    animation: pulse-critical 1.5s ease-in-out infinite;
}

.alert-pulse-warning {
    background: var(--warning);
}

@keyframes pulse-critical {
    0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.5); }
    50% { box-shadow: 0 0 0 6px rgba(220, 38, 38, 0); }
}

.alert-content { flex: 1; }

.alert-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.alert-meta {
    font-size: 12px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
}

.alert-time {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-dim);
    white-space: nowrap;
    margin-left: auto;
}

/* ── AI Analysis result ── */
.ai-result {
    margin-top: 16px;
    padding: 20px;
    background: var(--bg-primary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
}

.ai-result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--accent);
}

.ai-field {
    margin-bottom: 12px;
}

.ai-field-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 4px;
}

.ai-field-value {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.5;
}

.ai-provider-tag {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid var(--border-subtle);
}

/* ── Alert details grid ── */
.alert-details-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border-subtle);
}

.detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
}

.detail-value {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-primary);
}

/* ── Model Comparison Panels ── */
.model-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.model-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    border-bottom: 1px solid var(--border-subtle);
}

.model-name {
    font-size: 16px;
    font-weight: 700;
    font-family: var(--font-mono);
    display: flex;
    align-items: center;
    gap: 8px;
}

.model-tag {
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 2px 8px;
    border-radius: 10px;
}

.model-tag-statistical {
    background: rgba(37, 99, 235, 0.1);
    color: var(--accent);
    border: 1px solid rgba(37, 99, 235, 0.2);
}

.model-tag-forecast {
    background: rgba(244, 114, 182, 0.1);
    color: #f472b6;
    border: 1px solid rgba(244, 114, 182, 0.2);
}

.winner-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    color: var(--healthy);
}

.model-metrics-grid {
    padding: 20px 24px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.model-metric-box {
    text-align: center;
    padding: 12px;
    background: var(--bg-primary);
    border-radius: var(--radius-md);
}

.model-metric-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 6px;
}

.model-metric-value {
    font-family: var(--font-mono);
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
}

.model-metric-value.best { color: var(--healthy); }
.model-metric-value.worse { color: var(--text-secondary); }

.model-extra-grid {
    padding: 0 24px 20px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.extra-metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--bg-primary);
    border-radius: var(--radius-sm);
}

.extra-metric-label {
    font-size: 11px;
    color: var(--text-muted);
}

.extra-metric-value {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
}

/* ── Line Health Bars ── */
.line-health-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    background: var(--bg-primary);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    margin-bottom: 8px;
}

.line-health-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    width: 140px;
}

.line-bar-track {
    flex: 1;
    height: 6px;
    background: var(--border-subtle);
    border-radius: 3px;
    overflow: hidden;
}

.line-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.8s ease;
}

.line-health-pct {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    width: 45px;
    text-align: right;
}

/* ── Compact alert items for overview ── */
.alert-item-compact {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: var(--bg-primary);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    margin-bottom: 8px;
}

.alert-item-compact.critical-alert {
    border-left: 3px solid var(--critical);
    background: var(--critical-bg);
}

.alert-item-compact.warning-alert {
    border-left: 3px solid var(--warning);
    background: var(--warning-bg);
}

.alert-item-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
}

.alert-item-meta {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
}

/* ── Card wrapper ── */
.rs-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}

.card-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 16px;
}

/* ── Stat boxes for Sensor Explorer ── */
.stat-box {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px;
    text-align: center;
}

.stat-label {
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.stat-value {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
}

/* ── Page header styling ── */
.page-header-container {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
}

.page-title {
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: var(--text-primary);
    margin: 0;
    font-family: var(--font-sans);
}

.page-subtitle {
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
}

.header-time {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
    text-align: right;
}

.time-value {
    font-size: 18px;
    color: var(--text-primary);
    font-weight: 600;
    letter-spacing: -0.5px;
}

/* ── Anomaly score cells ── */
.anomaly-score {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    font-family: var(--font-mono);
}

.anomaly-score-high {
    background: var(--critical-bg);
    color: var(--critical);
}

.anomaly-score-medium {
    background: var(--warning-bg);
    color: var(--warning);
}

/* ── Data table styling ── */
.rs-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.rs-table thead th {
    text-align: left;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    padding: 8px 16px;
    border-bottom: 1px solid var(--border-default);
    font-family: var(--font-sans);
}

.rs-table tbody td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-subtle);
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-secondary);
}

.rs-table tbody tr:hover {
    background: var(--bg-card-hover);
}

/* ── VS badge ── */
.vs-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 20px;
    border-radius: var(--radius-sm);
    font-size: 9px;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text-dim);
    background: var(--bg-primary);
    border: 1px solid var(--border-subtle);
}

/* ── Streamlit expander override ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    background: var(--bg-card) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    overflow: hidden;
}

/* ── Streamlit selectbox / multiselect override ── */
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: var(--text-muted) !important;
}

/* ── Button overrides ── */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
}

.stButton > button:hover {
    background: #1d4ed8 !important;
    transform: translateY(-1px);
}

/* AI analysis button special styling */
.ai-btn .stButton > button {
    background: var(--accent-bg) !important;
    color: var(--accent) !important;
    border: 1px solid rgba(37, 99, 235, 0.2) !important;
}

.ai-btn .stButton > button:hover {
    background: rgba(37, 99, 235, 0.15) !important;
    border-color: rgba(37, 99, 235, 0.4) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── Status dot animation ── */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(5, 150, 105, 0.4); }
    50% { opacity: 0.7; box-shadow: 0 0 0 4px rgba(5, 150, 105, 0); }
}

.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--healthy);
    animation: pulse-dot 2s ease-in-out infinite;
    vertical-align: middle;
}

/* ── Filter chips ── */
.filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid var(--border-default);
    background: var(--bg-card);
    color: var(--text-secondary);
    margin-right: 8px;
}

.filter-chip-critical {
    background: var(--critical-bg);
    border-color: var(--critical-border);
    color: var(--critical);
}

.filter-chip-warning {
    background: var(--warning-bg);
    border-color: var(--warning-border);
    color: var(--warning);
}

.filter-chip-all {
    background: var(--accent-bg);
    border-color: rgba(37, 99, 235, 0.3);
    color: var(--accent);
}

.chip-count {
    font-family: var(--font-mono);
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 8px;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 0 0 32px 0;">
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:28px; height:28px; background:#2563eb; border-radius:6px;
                            display:flex; align-items:center; justify-content:center;
                            font-family:'JetBrains Mono',monospace; font-size:11px;
                            font-weight:700; color:white;">RS</div>
                <span style="font-family:'JetBrains Mono',monospace; font-size:15px;
                             font-weight:700; letter-spacing:-0.5px; color:#1e293b;">
                    RailSense-AI
                </span>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:4px;
                        font-weight:400; letter-spacing:0.5px; text-transform:uppercase;">
                Anomaly Detection Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        ["Live Overview", "Sensor Explorer", "Alert Feed", "Model Comparison"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        '<div style="font-family:\'JetBrains Mono\',monospace; font-size:11px; color:#64748b;">'
        '<span class="status-dot"></span>&nbsp;&nbsp;System Online</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(endpoint: str, params: dict | None = None) -> list[dict]:
    try:
        r = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return []


def page_header(title: str, subtitle: str):
    """Render styled page header with live clock."""
    now = datetime.now()
    st.markdown(
        f"""
        <div class="page-header-container">
            <div>
                <h2 class="page-title">{title}</h2>
                <div class="page-subtitle">{subtitle}</div>
            </div>
            <div class="header-time">
                <div class="time-value">{now.strftime("%H:%M:%S")}</div>
                <div>{now.strftime("%d %b %Y")} &middot; SGT</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def line_badge_html(line_id: str) -> str:
    """Return an HTML line badge for a given line ID."""
    code = line_id.upper().replace("LINE_", "").replace("LINE-", "")
    css_class = {
        "NSL": "line-nsl", "EWL": "line-ewl", "CCL": "line-ccl",
        "DTL": "line-dtl", "NEL": "line-nel", "TEL": "line-tel",
    }.get(code, "line-nsl")
    return f'<span class="line-badge {css_class}">{code}</span>'


def severity_badge_html(severity: str) -> str:
    """Return an HTML severity badge."""
    s = severity.lower()
    return f'<span class="severity-badge severity-{s}">{severity.upper()}</span>'


def anomaly_score_html(score: float) -> str:
    """Return an HTML anomaly score chip."""
    cls = "anomaly-score-high" if score >= 0.8 else "anomaly-score-medium"
    return f'<span class="anomaly-score {cls}">{score:.2f}</span>'


def make_plotly_layout(title: str = "", height: int = 360) -> dict:
    """Shared Plotly layout dict matching the design system."""
    return dict(
        template="plotly_white",
        height=height,
        margin=dict(l=50, r=20, t=40 if title else 20, b=40),
        title=dict(text=title, font=dict(family="DM Sans", size=14, color="#1e293b")) if title else None,
        font=dict(family="JetBrains Mono", size=11, color="#64748b"),
        xaxis=dict(
            gridcolor="#e2e8f0", linecolor="#e2e8f0",
            tickfont=dict(family="JetBrains Mono", size=10, color="#94a3b8"),
        ),
        yaxis=dict(
            gridcolor="#e2e8f0", linecolor="#e2e8f0",
            tickfont=dict(family="JetBrains Mono", size=10, color="#94a3b8"),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )


# ---------------------------------------------------------------------------
# Page: Live Overview
# ---------------------------------------------------------------------------

if page == "Live Overview":
    page_header("Live Overview", "Real-time network health monitoring &middot; Singapore MRT")

    anomalies = fetch("/api/anomalies", {"limit": 500})

    # ── Metric Cards ──
    critical = [a for a in anomalies if a.get("severity") == "critical"]
    warnings = [a for a in anomalies if a.get("severity") == "warning"]
    trains = set(a.get("train_id", "") for a in anomalies)
    total = len(anomalies)
    health = max(0, 100 - total)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-critical">', unsafe_allow_html=True)
        st.metric("Critical Alerts", len(critical))
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-warning">', unsafe_allow_html=True)
        st.metric("Warnings", len(warnings))
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-info">', unsafe_allow_html=True)
        st.metric("Affected Trains", len(trains))
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-healthy">', unsafe_allow_html=True)
        st.metric("System Health", f"{health}%")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Line Health + Active Alerts — two columns ──
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown('<div class="rs-card"><div class="card-title">MRT Line Health</div>', unsafe_allow_html=True)

        # Compute per-line health from anomalies
        line_info = {
            "NSL": ("North South Line", "nsl-red"),
            "EWL": ("East West Line", "ewl-green"),
            "CCL": ("Circle Line", "ccl-orange"),
            "DTL": ("Downtown Line", "dtl-blue"),
            "NEL": ("North East Line", "nel-purple"),
        }

        line_anomaly_counts: dict[str, int] = {}
        for a in anomalies:
            lid = a.get("line_id", "").upper()
            line_anomaly_counts[lid] = line_anomaly_counts.get(lid, 0) + 1

        for code, (name, _) in line_info.items():
            count = line_anomaly_counts.get(code, 0)
            pct = max(0, 100 - count * 7)
            if pct >= 95:
                bar_color = "#059669"
                pct_color = "#059669"
            elif pct >= 80:
                bar_color = "#d97706"
                pct_color = "#d97706"
            else:
                bar_color = f"linear-gradient(90deg, #d97706, #d42e12)"
                pct_color = "#d97706"

            badge_cls = f"line-{code.lower()}"
            st.markdown(
                f"""
                <div class="line-health-row">
                    <span class="line-badge {badge_cls}">{code}</span>
                    <span class="line-health-name">{name}</span>
                    <div class="line-bar-track">
                        <div class="line-bar-fill" style="width:{pct}%; background:{bar_color}"></div>
                    </div>
                    <span class="line-health-pct" style="color:{pct_color}">{pct}%</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="rs-card"><div class="card-title">Active Alerts</div>', unsafe_allow_html=True)

        display_anomalies = anomalies[:5] if anomalies else []
        for a in display_anomalies:
            sev = a.get("severity", "warning")
            alert_cls = "critical-alert" if sev == "critical" else "warning-alert"
            pulse_cls = "alert-pulse-critical" if sev == "critical" else "alert-pulse-warning"
            score = a.get("anomaly_score", 0)
            train = a.get("train_id", "")
            sensor = a.get("sensor_type", "")
            line = a.get("line_id", "")
            station = a.get("station_id", "")

            st.markdown(
                f"""
                <div class="alert-item-compact {alert_cls}">
                    <div class="alert-pulse {pulse_cls}"></div>
                    <div style="flex:1">
                        <div class="alert-item-title">{train} &middot; {sensor.replace('_', ' ').title()}</div>
                        <div class="alert-item-meta">{line} &middot; {station} &middot; Score: {score:.2f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not display_anomalies:
            st.markdown(
                '<div style="color:#64748b; font-size:13px; text-align:center; padding:20px;">No active alerts</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Recent Anomalies Table ──
    if anomalies:
        st.markdown('<div class="rs-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Recent Anomalies</div>', unsafe_allow_html=True)

        table_rows = ""
        for a in anomalies[:10]:
            ts = a.get("timestamp", "")
            if isinstance(ts, str) and "T" in ts:
                ts = ts.split("T")[-1][:8]
            sev = a.get("severity", "warning")
            score = a.get("anomaly_score", 0)
            method = a.get("detection_method", "")
            line = a.get("line_id", "").upper()
            table_rows += f"""
            <tr>
                <td>{ts}</td>
                <td>{a.get('train_id', '')}</td>
                <td>{line_badge_html(line)}</td>
                <td>{a.get('sensor_type', '')}</td>
                <td>{severity_badge_html(sev)}</td>
                <td>{anomaly_score_html(score)}</td>
                <td>{method}</td>
            </tr>
            """

        st.markdown(
            f"""
            <table class="rs-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Train ID</th>
                        <th>Line</th>
                        <th>Sensor</th>
                        <th>Severity</th>
                        <th>Score</th>
                        <th>Method</th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Sensor Explorer
# ---------------------------------------------------------------------------

elif page == "Sensor Explorer":
    page_header("Sensor Explorer", "Drill into individual sensor time-series with anomaly overlays")

    # ── Filters ──
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        train_id = st.selectbox("Train Unit", ["T001", "T002", "T003", "T004", "T005"])
    with fc2:
        sensor_type = st.selectbox("Sensor Type", ["vibration", "temperature", "door_cycle", "current_draw"])
    with fc3:
        time_range = st.selectbox("Time Range", ["Last 24 hours", "Last 48 hours", "Last 72 hours", "Last 7 days"])

    readings = fetch("/api/sensors", {"train_id": train_id, "sensor_type": sensor_type, "limit": 1000})

    if readings:
        df = pd.DataFrame(readings)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # ── Reading Stats ──
        s1, s2, s3, s4, s5 = st.columns(5)
        for col_obj, label, val, color in [
            (s1, "Data Points", str(len(df)), None),
            (s2, "Mean", f"{df['value'].mean():.2f}", None),
            (s3, "Std Dev", f"{df['value'].std():.3f}", None),
            (s4, "Max", f"{df['value'].max():.2f}", "#dc2626"),
            (s5, "Anomalies", "---", "#d97706"),
        ]:
            color_style = f'color:{color}' if color else ''
            col_obj.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value" style="{color_style}">{val}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Plotly chart ──
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["value"],
            mode="lines",
            name=f"{sensor_type} value",
            line=dict(color="#2563eb", width=1.5),
            hovertemplate="%{x|%H:%M:%S}<br>Value: %{y:.3f}<extra></extra>",
        ))

        # Overlay anomalies
        anomalies = fetch("/api/anomalies", {"train_id": train_id, "limit": 200})
        anom_df_all = pd.DataFrame()
        if anomalies:
            anom_df_full = pd.DataFrame(anomalies)
            anom_df_all = anom_df_full[anom_df_full["sensor_type"] == sensor_type].copy()
            if not anom_df_all.empty:
                anom_df_all["timestamp"] = pd.to_datetime(anom_df_all["timestamp"])
                # Merge to get values at anomaly timestamps
                merged = pd.merge_asof(
                    anom_df_all.sort_values("timestamp"),
                    df[["timestamp", "value"]].sort_values("timestamp"),
                    on="timestamp",
                    direction="nearest",
                    suffixes=("_anom", ""),
                )

                crit_mask = merged["severity"] == "critical"
                warn_mask = merged["severity"] == "warning"

                if crit_mask.any():
                    crit = merged[crit_mask]
                    fig.add_trace(go.Scatter(
                        x=crit["timestamp"],
                        y=crit["value"],
                        mode="markers",
                        name="Critical",
                        marker=dict(color="#dc2626", size=8, symbol="circle"),
                        hovertemplate="Critical<br>Score: %{customdata:.2f}<extra></extra>",
                        customdata=crit["anomaly_score"],
                    ))

                if warn_mask.any():
                    warn = merged[warn_mask]
                    fig.add_trace(go.Scatter(
                        x=warn["timestamp"],
                        y=warn["value"],
                        mode="markers",
                        name="Warning",
                        marker=dict(color="#d97706", size=7, symbol="circle"),
                        hovertemplate="Warning<br>Score: %{customdata:.2f}<extra></extra>",
                        customdata=warn["anomaly_score"],
                    ))

                # Update anomaly count stat
                s5.markdown(
                    f"""
                    <div class="stat-box">
                        <div class="stat-label">Anomalies</div>
                        <div class="stat-value" style="color:#d97706">{len(anom_df_all)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        fig.update_layout(**make_plotly_layout(height=360))
        fig.update_layout(
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(family="DM Sans", size=11),
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Anomaly Details Table ──
        if not anom_df_all.empty:
            st.markdown('<div class="rs-card"><div class="card-title">Detected Anomalies</div>', unsafe_allow_html=True)

            table_rows = ""
            for _, row in anom_df_all.iterrows():
                ts = str(row.get("timestamp", ""))
                if "T" in ts:
                    ts = ts.split("T")[-1][:8]
                elif " " in ts:
                    ts = ts.split(" ")[-1][:8]
                sev = row.get("severity", "warning")
                score = row.get("anomaly_score", 0)
                method = row.get("detection_method", "")
                table_rows += f"""
                <tr>
                    <td>{ts}</td>
                    <td>{anomaly_score_html(score)}</td>
                    <td>{severity_badge_html(sev)}</td>
                    <td>{method}</td>
                </tr>
                """

            st.markdown(
                f"""
                <table class="rs-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Score</th>
                            <th>Severity</th>
                            <th>Method</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="rs-card" style="text-align:center; color:#64748b; padding:40px;">'
            "No sensor data found. Run the seed script first.</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Page: Alert Feed
# ---------------------------------------------------------------------------

elif page == "Alert Feed":
    page_header("Alert Feed", "Review anomaly alerts and request AI-powered analysis")

    severity_filter = st.multiselect(
        "Filter by severity",
        ["critical", "warning"],
        default=["critical", "warning"],
    )

    anomalies = fetch("/api/anomalies", {"limit": 200})

    if anomalies:
        df = pd.DataFrame(anomalies)
        df = df[df["severity"].isin(severity_filter)]

        # ── Filter chips summary ──
        total_count = len(df)
        crit_count = len(df[df["severity"] == "critical"])
        warn_count = len(df[df["severity"] == "warning"])

        st.markdown(
            f"""
            <div style="display:flex; gap:8px; margin-bottom:24px;">
                <span class="filter-chip filter-chip-all">All <span class="chip-count">{total_count}</span></span>
                <span class="filter-chip filter-chip-critical">Critical <span class="chip-count">{crit_count}</span></span>
                <span class="filter-chip filter-chip-warning">Warning <span class="chip-count">{warn_count}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Alert Cards ──
        for _, row in df.iterrows():
            sev = row["severity"]
            border_cls = "alert-card-critical" if sev == "critical" else "alert-card-warning"
            pulse_cls = "alert-pulse-critical" if sev == "critical" else "alert-pulse-warning"
            score = row.get("anomaly_score", 0)
            train = row.get("train_id", "")
            sensor = row.get("sensor_type", "")
            line = row.get("line_id", "").upper()
            station = row.get("station_id", "")
            method = row.get("detection_method", "")
            ts = row.get("timestamp", "")

            line_badge = line_badge_html(line)

            alert_card_html = f"""
            <div class="alert-card {border_cls}">
                <div class="alert-header">
                    <div class="alert-pulse {pulse_cls}"></div>
                    <div class="alert-content">
                        <div class="alert-title">
                            {severity_badge_html(sev)}&nbsp;&nbsp;
                            {sensor.replace('_', ' ').title()} anomaly detected
                        </div>
                        <div class="alert-meta">
                            <span>{line_badge}&nbsp;{train}</span>
                            <span>{station}</span>
                            <span>{sensor}</span>
                            <span>{ts}</span>
                        </div>
                    </div>
                </div>
                <div class="alert-details-grid">
                    <div class="detail-item">
                        <span class="detail-label">Anomaly Score</span>
                        <span class="detail-value" style="color:{'#dc2626' if sev == 'critical' else '#d97706'}">{score:.2f}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Line / Station</span>
                        <span class="detail-value">{line} / {station}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Detection Method</span>
                        <span class="detail-value">{method}</span>
                    </div>
                </div>
            </div>
            """
            st.markdown(alert_card_html, unsafe_allow_html=True)

            # AI Analysis button
            col_btn, col_spacer = st.columns([1, 3])
            with col_btn:
                st.markdown('<div class="ai-btn">', unsafe_allow_html=True)
                if st.button("Request AI Analysis", key=f"assess_{row['id']}"):
                    with st.spinner("Analyzing..."):
                        try:
                            r = httpx.post(f"{API_BASE}/api/assess/{row['id']}", timeout=30.0)
                            if r.status_code == 200:
                                assessment = r.json()
                                root_cause = assessment.get("root_cause", "N/A")
                                action = assessment.get("recommended_action", "N/A")
                                reasoning = assessment.get("reasoning", "N/A")
                                sev_assess = assessment.get("severity_assessment", sev)
                                provider = assessment.get("provider", "AI Agent")
                                tokens = assessment.get("tokens_used", "---")

                                st.markdown(
                                    f"""
                                    <div class="ai-result">
                                        <div class="ai-result-header">&#9733; AI Agent Assessment</div>
                                        <div class="ai-field">
                                            <div class="ai-field-label">Root Cause</div>
                                            <div class="ai-field-value">{root_cause}</div>
                                        </div>
                                        <div class="ai-field">
                                            <div class="ai-field-label">Severity Assessment</div>
                                            <div class="ai-field-value">{severity_badge_html(sev_assess)} &mdash; AI-confirmed severity level</div>
                                        </div>
                                        <div class="ai-field">
                                            <div class="ai-field-label">Recommended Action</div>
                                            <div class="ai-field-value">{action}</div>
                                        </div>
                                        <div class="ai-field">
                                            <div class="ai-field-label">Reasoning</div>
                                            <div class="ai-field-value">{reasoning}</div>
                                        </div>
                                        <div class="ai-provider-tag">
                                            Analyzed by {provider} &middot; {tokens} tokens
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.error("Analysis failed")
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="rs-card" style="text-align:center; color:#64748b; padding:40px;">'
            "No anomalies detected yet.</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Page: Model Comparison
# ---------------------------------------------------------------------------

elif page == "Model Comparison":
    page_header("Model Comparison", "Compare STL decomposition vs Prophet forecast anomaly detection")

    st.markdown(
        '<div style="font-size:13px; color:#64748b; margin-bottom:24px;">'
        "Comparing detection performance on synthetic data with known anomalies.</div>",
        unsafe_allow_html=True,
    )

    if st.button("Run Comparison"):
        with st.spinner("Running STL and Prophet detectors... (Prophet may take a minute)"):
            from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario
            from src.detection.compare import compare_detectors

            gen = SyntheticGenerator(seed=99)
            scenario = AnomalyScenario(
                sensor_types=["temperature"], start_hour=12, duration_hours=2, magnitude=4.0
            )
            df = gen.generate(train_id="COMPARE", hours=48, anomalies=[scenario])
            temp_df = df[df["sensor_type"] == "temperature"].reset_index(drop=True)

            metrics = compare_detectors(temp_df)

            # ── Side-by-side model panels ──
            col_stl, col_prophet = st.columns(2)

            model_configs = {
                "stl": {
                    "col": col_stl,
                    "name": "STL Decomposition",
                    "tag_cls": "model-tag-statistical",
                    "tag_text": "Statistical",
                },
                "prophet": {
                    "col": col_prophet,
                    "name": "Prophet Forecast",
                    "tag_cls": "model-tag-forecast",
                    "tag_text": "Forecast",
                },
            }

            # Determine winners
            stl_m = metrics.get("stl", {})
            prophet_m = metrics.get("prophet", {})

            for key, cfg in model_configs.items():
                m = metrics.get(key, {})
                prec = m.get("precision", 0)
                rec = m.get("recall", 0)
                f1 = m.get("f1", 0)
                time_s = m.get("time_seconds", 0)
                flagged = m.get("total_flagged", 0)
                tp = m.get("true_positives", "---")
                fp = m.get("false_positives", "---")

                # Determine winner text
                winner_parts = []
                if key == "stl":
                    if stl_m.get("f1", 0) >= prophet_m.get("f1", 0):
                        winner_parts.append("Higher F1")
                    if stl_m.get("precision", 0) >= prophet_m.get("precision", 0):
                        winner_parts.append("Higher Precision")
                else:
                    if prophet_m.get("recall", 0) >= stl_m.get("recall", 0):
                        winner_parts.append("Higher Recall")

                winner_html = ""
                if winner_parts:
                    winner_html = f'<div class="winner-indicator">&#9733; {", ".join(winner_parts)}</div>'

                prec_cls = "best" if (key == "stl" and prec >= prophet_m.get("precision", 0)) or (key == "prophet" and prec > stl_m.get("precision", 0)) else "worse"
                rec_cls = "best" if (key == "stl" and rec >= prophet_m.get("recall", 0)) or (key == "prophet" and rec > stl_m.get("recall", 0)) else "worse"
                f1_cls = "best" if (key == "stl" and f1 >= prophet_m.get("f1", 0)) or (key == "prophet" and f1 > stl_m.get("f1", 0)) else "worse"

                time_color = "#059669" if time_s < 1 else "#d97706"

                with cfg["col"]:
                    st.markdown(
                        f"""
                        <div class="model-panel">
                            <div class="model-panel-header">
                                <div class="model-name">
                                    {cfg['name']}
                                    <span class="model-tag {cfg['tag_cls']}">{cfg['tag_text']}</span>
                                </div>
                                {winner_html}
                            </div>
                            <div class="model-metrics-grid">
                                <div class="model-metric-box">
                                    <div class="model-metric-label">Precision</div>
                                    <div class="model-metric-value {prec_cls}">{prec:.2f}</div>
                                </div>
                                <div class="model-metric-box">
                                    <div class="model-metric-label">Recall</div>
                                    <div class="model-metric-value {rec_cls}">{rec:.2f}</div>
                                </div>
                                <div class="model-metric-box">
                                    <div class="model-metric-label">F1 Score</div>
                                    <div class="model-metric-value {f1_cls}">{f1:.2f}</div>
                                </div>
                            </div>
                            <div class="model-extra-grid">
                                <div class="extra-metric">
                                    <span class="extra-metric-label">Compute Time</span>
                                    <span class="extra-metric-value" style="color:{time_color}">{time_s:.2f}s</span>
                                </div>
                                <div class="extra-metric">
                                    <span class="extra-metric-label">Total Flagged</span>
                                    <span class="extra-metric-value">{flagged}</span>
                                </div>
                                <div class="extra-metric">
                                    <span class="extra-metric-label">True Positives</span>
                                    <span class="extra-metric-value">{tp}</span>
                                </div>
                                <div class="extra-metric">
                                    <span class="extra-metric-label">False Positives</span>
                                    <span class="extra-metric-value">{fp}</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # ── Chart: Sensor data with anomaly window ──
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            fig = go.Figure()

            temp_df_sorted = temp_df.sort_values("timestamp").copy()
            temp_df_sorted["timestamp"] = pd.to_datetime(temp_df_sorted["timestamp"])

            fig.add_trace(go.Scatter(
                x=temp_df_sorted["timestamp"],
                y=temp_df_sorted["value"],
                mode="lines",
                name="Sensor Value",
                line=dict(color="#2563eb", width=2),
                hovertemplate="%{x|%H:%M}<br>Value: %{y:.3f}<extra></extra>",
            ))

            # Mark anomaly window (hours 12-14 based on scenario)
            min_ts = temp_df_sorted["timestamp"].min()
            anom_start = min_ts + pd.Timedelta(hours=12)
            anom_end = min_ts + pd.Timedelta(hours=14)

            fig.add_vrect(
                x0=anom_start, x1=anom_end,
                fillcolor="rgba(220, 38, 38, 0.06)",
                line=dict(color="#dc2626", width=1, dash="dash"),
                annotation_text="Known Anomaly",
                annotation_position="top left",
                annotation_font=dict(family="JetBrains Mono", size=9, color="#dc2626"),
            )

            fig.update_layout(**make_plotly_layout(title="Sensor Data with Anomaly Predictions", height=320))
            fig.update_layout(
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(family="DM Sans", size=11),
                ),
            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # ── Comparison Summary Table ──
            st.markdown('<div class="rs-card"><div class="card-title">Detailed Comparison Summary</div>', unsafe_allow_html=True)

            stl_prec = stl_m.get("precision", 0)
            stl_rec = stl_m.get("recall", 0)
            stl_f1 = stl_m.get("f1", 0)
            stl_time = stl_m.get("time_seconds", 0)
            pr_prec = prophet_m.get("precision", 0)
            pr_rec = prophet_m.get("recall", 0)
            pr_f1 = prophet_m.get("f1", 0)
            pr_time = prophet_m.get("time_seconds", 0)

            def winner_cell(stl_val, pr_val, higher_is_better=True):
                if higher_is_better:
                    w = "STL" if stl_val >= pr_val else "Prophet"
                else:
                    w = "STL" if stl_val <= pr_val else "Prophet"
                return f'<span class="severity-badge severity-healthy">{w}</span>'

            def val_style(val, other_val, higher_is_better=True):
                is_better = (val >= other_val) if higher_is_better else (val <= other_val)
                return 'color: #059669; font-weight: 600' if is_better else ''

            st.markdown(
                f"""
                <table class="rs-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>STL Decomposition</th>
                            <th></th>
                            <th>Prophet Forecast</th>
                            <th>Winner</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="color:#1e293b; font-family:'DM Sans',sans-serif">Precision</td>
                            <td style="{val_style(stl_prec, pr_prec)}">{stl_prec:.2f}</td>
                            <td><span class="vs-badge">vs</span></td>
                            <td style="{val_style(pr_prec, stl_prec)}">{pr_prec:.2f}</td>
                            <td>{winner_cell(stl_prec, pr_prec)}</td>
                        </tr>
                        <tr>
                            <td style="color:#1e293b; font-family:'DM Sans',sans-serif">Recall</td>
                            <td style="{val_style(stl_rec, pr_rec)}">{stl_rec:.2f}</td>
                            <td><span class="vs-badge">vs</span></td>
                            <td style="{val_style(pr_rec, stl_rec)}">{pr_rec:.2f}</td>
                            <td>{winner_cell(stl_rec, pr_rec)}</td>
                        </tr>
                        <tr>
                            <td style="color:#1e293b; font-family:'DM Sans',sans-serif">F1 Score</td>
                            <td style="{val_style(stl_f1, pr_f1)}">{stl_f1:.2f}</td>
                            <td><span class="vs-badge">vs</span></td>
                            <td style="{val_style(pr_f1, stl_f1)}">{pr_f1:.2f}</td>
                            <td>{winner_cell(stl_f1, pr_f1)}</td>
                        </tr>
                        <tr>
                            <td style="color:#1e293b; font-family:'DM Sans',sans-serif">Computation Time</td>
                            <td style="{val_style(stl_time, pr_time, higher_is_better=False)}">{stl_time:.2f}s</td>
                            <td><span class="vs-badge">vs</span></td>
                            <td style="{val_style(pr_time, stl_time, higher_is_better=False)}">{pr_time:.2f}s</td>
                            <td>{winner_cell(stl_time, pr_time, higher_is_better=False)}</td>
                        </tr>
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
