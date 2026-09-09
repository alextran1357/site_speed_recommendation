import html
import math
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import streamlit as st

from utils.audit_evidence import lcp_item, lcp_image_finding
from utils.platform_guidance import PLATFORM_HELP, PLATFORM_OPTIONS, PLATFORM_SUPPORT, guidance_for


PRIMARY_METRICS = [
    {
        "label": "Largest Contentful Paint",
        "key": "largest-contentful-paint",
        "short": "LCP",
        "unit": "ms",
        "category": "Loading speed",
        "tier": "Core Web Vital",
        "lower_is_better": True,
        "thresholds": (2500, 4000),
        "scale_max": 6000,
        "basis": "Core Web Vitals: good <= 2.5s, needs improvement <= 4.0s, poor > 4.0s.",
        "recommendation": "Find the page element reported as the LCP element, then reduce how long it takes to load and render. Start with image sizing/compression, preload only the hero asset when appropriate, and remove render-blocking work before it appears.",
        "resource_url": "https://web.dev/articles/optimize-lcp",
        "resource_label": "web.dev LCP optimization guide",
    },
    {
        "label": "Cumulative Layout Shift",
        "key": "cumulative-layout-shift",
        "short": "CLS",
        "unit": "score",
        "category": "Visual stability",
        "tier": "Core Web Vital",
        "lower_is_better": True,
        "thresholds": (0.1, 0.25),
        "scale_max": 0.35,
        "basis": "Core Web Vitals: good <= 0.10, needs improvement <= 0.25, poor > 0.25.",
        "recommendation": "Look for elements that move after the page starts rendering. Reserve fixed space for images, ads, embeds, banners, and late-loading UI so the layout stays stable.",
        "resource_url": "https://web.dev/articles/optimize-cls",
        "resource_label": "web.dev CLS optimization guide",
    },
    {
        "label": "Interaction to Next Paint",
        "key": "INTERACTION_TO_NEXT_PAINT",
        "short": "INP",
        "unit": "ms",
        "category": "Responsiveness",
        "tier": "Core Web Vital",
        "lower_is_better": True,
        "thresholds": (200, 500),
        "scale_max": 800,
        "basis": "Core Web Vitals: good <= 200ms, needs improvement <= 500ms, poor > 500ms.",
        "recommendation": "Find the slowest interaction, then reduce main-thread work around that interaction. Break up long JavaScript tasks, defer non-critical scripts, and keep event handlers small.",
        "resource_url": "https://web.dev/articles/optimize-inp",
        "resource_label": "web.dev INP optimization guide",
    },
]

FIELD_METRICS = [
    {**PRIMARY_METRICS[0], "key": "field_largest-contentful-paint"},
    {**PRIMARY_METRICS[1], "key": "field_cumulative-layout-shift"},
    PRIMARY_METRICS[2].copy(),
]

SECONDARY_METRICS = [
    {
        "label": "Performance Score",
        "key": "performance_score",
        "short": "Performance",
        "unit": "score_percent",
        "category": "Overall score",
        "tier": "PageSpeed signal",
        "lower_is_better": False,
        "thresholds": (0.9, 0.5),
        "scale_max": 1,
        "basis": "Lighthouse score: good >= 90, needs improvement >= 50, poor < 50.",
        "recommendation": "Use this as a summary signal, then use the metric breakdown to decide what to fix first.",
    },
    {
        "label": "First Contentful Paint",
        "key": "first-contentful-paint",
        "short": "FCP",
        "unit": "ms",
        "category": "Loading speed",
        "tier": "PageSpeed signal",
        "lower_is_better": True,
        "thresholds": (1800, 3000),
        "scale_max": 5000,
        "basis": "Lighthouse scoring guidance: good <= 1.8s, needs improvement <= 3.0s, poor > 3.0s.",
        "recommendation": "Reduce render-blocking CSS and scripts so the first visible content appears sooner.",
    },
    {
        "label": "Total Blocking Time",
        "key": "total-blocking-time",
        "short": "TBT",
        "unit": "ms",
        "category": "Main thread work",
        "tier": "PageSpeed signal",
        "lower_is_better": True,
        "thresholds": (200, 600),
        "scale_max": 1000,
        "basis": "Lighthouse scoring guidance: good <= 200ms, needs improvement <= 600ms, poor > 600ms.",
        "recommendation": "Reduce long JavaScript tasks, remove unused code, and defer work that is not needed for the first interaction.",
    },
    {
        "label": "Speed Index",
        "key": "speed-index",
        "short": "Speed Index",
        "unit": "ms",
        "category": "Visual loading",
        "tier": "PageSpeed signal",
        "lower_is_better": True,
        "thresholds": (3400, 5800),
        "scale_max": 9000,
        "basis": "Lighthouse scoring guidance: good <= 3.4s, needs improvement <= 5.8s, poor > 5.8s.",
        "recommendation": "Prioritize above-the-fold rendering and reduce large render-blocking resources.",
    },
    {
        "label": "Time to First Byte",
        "key": "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
        "short": "TTFB",
        "unit": "ms",
        "category": "Server response",
        "tier": "PageSpeed signal",
        "lower_is_better": True,
        "thresholds": (800, 1800),
        "scale_max": 3000,
        "basis": "Server response guidance: good <= 800ms, needs improvement <= 1.8s, poor > 1.8s.",
        "recommendation": "Improve hosting, caching, CDN behavior, and backend response time before front-end rendering begins.",
    },
    {
        "label": "Time to Interactive",
        "key": "interactive",
        "short": "Interactive",
        "unit": "ms",
        "category": "Interactivity",
        "tier": "PageSpeed signal",
        "lower_is_better": True,
        "thresholds": (3800, 7300),
        "scale_max": 10000,
        "basis": "Lighthouse scoring guidance: good <= 3.8s, needs improvement <= 7.3s, poor > 7.3s.",
        "recommendation": "Reduce JavaScript execution and main-thread work so the page becomes reliably usable sooner.",
    },
]

METRIC_DEFINITIONS = PRIMARY_METRICS + SECONDARY_METRICS
FIELD_DATA_KEYS = {"INTERACTION_TO_NEXT_PAINT", "EXPERIMENTAL_TIME_TO_FIRST_BYTE"}
PRIORITY_ISSUES = (
    ("lcp", "field_largest-contentful-paint", "largest-contentful-paint"),
    ("cls", "field_cumulative-layout-shift", "cumulative-layout-shift"),
    ("responsiveness", "INTERACTION_TO_NEXT_PAINT", "total-blocking-time"),
)

def inject_dashboard_styles():
    st.markdown(
        """
        <style>
            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stSidebar"] {background: #111827 !important;}
            .stApp, .stApp p, .stApp label, .stApp span, .stApp div,
            .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {color: #e5e7eb !important;}
            .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
            [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"], .small-muted {color: #cbd5e1 !important;}
            .benchmark-card {
                background: #1f2937 !important;
                border: 1px solid #334155;
                border-radius: 8px;
                box-shadow: none;
            }
            .benchmark-card h4 {margin: 0 0 8px 0; color: #f8fafc !important;}
            .benchmark-card p {margin: 0; color: #cbd5e1 !important; line-height: 1.5;}
            .status-good {color: #34d399 !important; font-weight: 750;}
            .status-watch {color: #fbbf24 !important; font-weight: 750;}
            .status-poor {color: #f87171 !important; font-weight: 750;}
            .compact-metric {padding: 0 0 4px; min-height: 68px;}
            .compact-label {font-size: 0.8rem; font-weight: 650; color: #cbd5e1 !important; margin-bottom: 1px;}
            .compact-value {font-size: 1.75rem; line-height: 1.05; font-weight: 800; margin-bottom: 2px;}
            .compact-value.status-good {color: #34d399 !important;}
            .compact-value.status-watch {color: #fbbf24 !important;}
            .compact-value.status-poor {color: #f87171 !important;}
            .compact-value.small-muted {color: #94a3b8 !important;}
            .compact-meta {font-size: 0.72rem; color: #94a3b8 !important;}
            .compact-meta .status-good {color: #34d399 !important;}
            .compact-meta .status-watch {color: #fbbf24 !important;}
            .compact-meta .status-poor {color: #f87171 !important;}
            .data-source-header {margin: 0 0 6px;}
            .data-source-header .data-source-title {font-size: 1.1rem; line-height: 1.25; font-weight: 800; color: #f8fafc !important;}
            .data-source-header .data-source-context {margin-top: 1px; font-size: 0.78rem; line-height: 1.35; color: #94a3b8 !important;}
            .metric-section-divider {border-top: 1px solid #334155; margin: 2px 0 8px;}
            .meaning-card {background: #172033; border: 1px solid #475569; border-left: 4px solid #60a5fa; border-radius: 8px; padding: 16px 18px; margin: 24px 0 0;}
            .meaning-card.good {border-left-color: #34d399;}
            .meaning-card.caution {border-left-color: #fbbf24;}
            .meaning-card.poor {border-left-color: #f87171;}
            .meaning-label {font-size: 0.72rem; font-weight: 850; letter-spacing: 0.08em; text-transform: uppercase; color: #94a3b8 !important;}
            .meaning-title {font-size: 1.1rem; font-weight: 800; color: #f8fafc !important; margin: 3px 0 6px;}
            .meaning-body {margin: 0; color: #e2e8f0 !important; line-height: 1.5;}
            .benchmark-card {padding: 16px 18px; margin-bottom: 14px;}
            .benchmark-header {display: flex; justify-content: space-between; gap: 16px; align-items: baseline;}
            .benchmark-title {font-size: 1.08rem; font-weight: 750; color: #f8fafc !important;}
            .benchmark-percentile {font-size: 1.45rem; font-weight: 800; text-align: right;}
            .benchmark-track {position: relative; height: 16px; border-radius: 999px; overflow: visible; margin: 14px 0 10px 0; border: 1px solid #64748b;}
            .threshold-track {background: linear-gradient(90deg, #22c55e 0%, #22c55e var(--good-end), #f59e0b var(--good-end), #f59e0b var(--warn-end), #ef4444 var(--warn-end), #ef4444 100%);}
            .score-track {background: linear-gradient(90deg, #ef4444 0%, #ef4444 50%, #f59e0b 50%, #f59e0b 90%, #22c55e 90%, #22c55e 100%);}
            .benchmark-marker {position: absolute; top: -6px; height: 28px; width: 5px; background: #f8fafc; border: 2px solid #111827; border-radius: 999px; box-shadow: 0 0 0 1px #f8fafc; transform: translateX(-50%); z-index: 2;}
            .scale-labels {display: flex; justify-content: space-between; color: #cbd5e1 !important; font-size: 0.78rem; margin-bottom: 8px;}
            .scale-labels span {color: #cbd5e1 !important;}
            .scale-labels span.status-good {color: #34d399 !important;}
            .scale-labels span.status-watch {color: #fbbf24 !important;}
            .scale-labels span.status-poor {color: #f87171 !important;}
            .benchmark-meta {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px;}
            .benchmark-meta div {background: #273449; border-radius: 6px; padding: 8px 10px; color: #f8fafc !important;}
            .benchmark-meta span {display: block; color: #cbd5e1 !important; font-size: 0.78rem;}
            .recommendations-heading {font-size: 2rem; line-height: 1.2; font-weight: 800; color: #f8fafc !important; margin: 28px 0 12px;}
            .priority-card {background: #1f2937; border: 1px solid #475569; border-radius: 8px; padding: 20px 22px; margin-bottom: 18px;}
            .priority-eyebrow {font-size: 0.75rem; font-weight: 850; letter-spacing: 0.08em; text-transform: uppercase;}
            .priority-eyebrow.status-good {color: #34d399 !important;}
            .priority-eyebrow.status-watch {color: #fbbf24 !important;}
            .priority-eyebrow.status-poor {color: #f87171 !important;}
            .priority-title {font-size: 1.2rem; font-weight: 800; color: #f8fafc !important; margin: 4px 0 10px;}
            .priority-measurement {display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px 14px;}
            .priority-value {font-size: 1rem; font-weight: 750;}
            .priority-value.status-good {color: #34d399 !important;}
            .priority-value.status-watch {color: #fbbf24 !important;}
            .priority-value.status-poor {color: #f87171 !important;}
            .priority-target {font-size: 0.9rem; color: #cbd5e1 !important;}
            .priority-impact {font-size: 1rem; line-height: 1.5; color: #e2e8f0 !important; margin: 8px 0;}
            .priority-peer {font-size: 0.8rem; color: #94a3b8 !important; margin-top: 2px;}
            .priority-fix {background: #273449; border-left: 3px solid #60a5fa; border-radius: 5px; padding: 12px 14px; margin-top: 14px;}
            .priority-fix-label {font-size: 0.7rem; font-weight: 850; letter-spacing: 0.07em; text-transform: uppercase; color: #93c5fd !important;}
            .priority-fix-title {font-size: 1rem; font-weight: 800; color: #f8fafc !important; margin-top: 2px;}
            .priority-fix p {margin: 5px 0 0; color: #cbd5e1 !important; line-height: 1.45;}
            .priority-help {border-top: 1px solid #475569; margin-top: 12px; padding-top: 12px;}
            .fix-evidence {font-size: 0.85rem; line-height: 1.5; color: #cbd5e1 !important; margin-top: 14px;}
            .resource-link.priority-link {border-color: #60a5fa;}
            .priority-card.secondary-fix {padding: 18px 20px; border-color: #334155;}
            [class*="st-key-recommendation_"] {background: #1f2937; border: 1px solid #475569; border-radius: 8px; padding: 20px 22px; margin-bottom: 18px;}
            [class*="st-key-recommendation_"]:has(.secondary-fix) {padding: 18px 20px; border-color: #334155;}
            [class*="st-key-recommendation_"] .priority-card {border: 0; padding: 0; margin: 0;}
            [class*="st-key-owner_help_"] {background: #273449; border-left: 3px solid #60a5fa; border-radius: 5px; padding: 12px 14px;}
            [class*="st-key-owner_help_"] .priority-help {border: 0; padding: 0; margin: 0;}
            [class*="st-key-owner_help_"] p {margin: 5px 0 0; color: #cbd5e1 !important; line-height: 1.45;}


            .secondary-fix .priority-title {font-size: 1.1rem;}
            .resource-link {display: inline-flex; align-items: center; box-sizing: border-box; max-width: 100%; min-height: 44px; padding: 9px 12px; border: 1px solid #64748b; border-radius: 6px; margin-top: 10px; color: #93c5fd !important; font-weight: 700; text-decoration: none; overflow-wrap: anywhere;}
            .resource-link:hover {background: #334155; text-decoration: underline;}
            .resource-link:focus-visible {outline: 2px solid #93c5fd; outline-offset: 3px;}
            .platform-help .resource-link {margin-top: 0; font-size: 0.875rem; font-weight: 600;}
            [data-testid="stPopover"] button {border: 1px solid #64748b; background: #273449; color: #f8fafc;}
            [data-testid="stPopoverBody"] {background: #1f2937; border: 1px solid #64748b;}
            [data-testid="stPopoverBody"] > div {background: #1f2937;}
            [data-testid="stPopoverBody"] [data-testid="stCode"] pre {background: #111827;}
            [data-testid="stPopoverBody"] [data-testid="stCode"] code {color: #e2e8f0;}
            [data-testid="stPopoverBody"] [data-testid="stCode"] > div {opacity: 1 !important; visibility: visible !important;}

            [data-testid="stSelectbox"] label[data-testid="stWidgetLabel"] {display: inline-flex !important; width: fit-content !important; align-items: center; gap: 4px;}
            [data-testid="stSelectbox"] label[data-testid="stWidgetLabel"] > div {flex: 0 0 auto !important; margin-left: 0 !important;}
            [data-testid="stSelectbox"] [data-testid="stTooltipIcon"] {margin-left: 0 !important;}
            div[data-baseweb="input"] input, div[data-baseweb="select"] > div, textarea {background: #1f2937 !important; color: #f9fafb !important; border-color: #475569 !important;}
            div[role="radiogroup"] label span, [data-baseweb="tab"] p {color: #e5e7eb !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_url(url):
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def available_categories(metric_data):
    categories = {
        category
        for data in metric_data["largest-contentful-paint"].values()
        for category in data["category"].dropna().unique()
        if category != "null"
    }
    return sorted(categories)


def get_reference_data(metric_data, metric, device, category, scope):
    """Return benchmark data for read-only use; callers must not mutate it."""
    reference_data = metric_data[metric][device]
    if scope == "Selected category":
        scoped = reference_data[reference_data["category"] == category]
        if len(scoped) >= 20:
            return scoped, f"{category} {device} pages"
        return reference_data, f"all {device} pages; selected category sample was too small"
    return reference_data, f"all {device} pages"


def clean_number(value):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def format_value(value, unit):
    value = clean_number(value)
    if value is None:
        return "Unavailable"
    if unit == "score_percent":
        return f"{value * 100:.0f}" if value <= 1 else f"{value:.0f}"
    if unit == "score":
        return f"{value:.3f}" if abs(value) < 10 else f"{value:,.0f}"
    if unit == "ms":
        return f"{value / 1000:.2f} s" if value >= 1000 else f"{value:,.0f} ms"
    if unit == "bytes":
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.2f} MB"
        if value >= 1024:
            return f"{value / 1024:.0f} KB"
        return f"{value:,.0f} B"
    return f"{value:,.0f}"


def worse_percentile_for(reference_data, metric_def, value):
    value = clean_number(value)
    metric = metric_def["key"]
    if value is None or metric not in reference_data.columns:
        return None
    series = pd.to_numeric(reference_data[metric], errors="coerce").dropna()
    if series.empty:
        return None

    values = series.to_numpy(dtype=float)
    if metric_def["lower_is_better"]:
        worse_or_equal = np.sum(values <= value)
    else:
        worse_or_equal = np.sum(values >= value)
    return float(np.clip((worse_or_equal / len(values)) * 100, 0, 100))


def peer_median(reference_data, metric, unit):
    if metric not in reference_data.columns:
        return "Unavailable"
    series = pd.to_numeric(reference_data[metric], errors="coerce").dropna()
    if series.empty:
        return "Unavailable"
    return format_value(series.median(), unit)


def threshold_status(metric_def, value):
    value = clean_number(value)
    if value is None:
        return "Unavailable", "small-muted"
    good, warn = metric_def["thresholds"]
    if metric_def["lower_is_better"]:
        if value <= good:
            return "Good", "status-good"
        if value <= warn:
            return "Needs improvement", "status-watch"
        return "Poor", "status-poor"
    if value >= good:
        return "Good", "status-good"
    if value >= warn:
        return "Needs improvement", "status-watch"
    return "Poor", "status-poor"


def marker_position_for(metric_def, value):
    value = clean_number(value)
    if value is None:
        return 0
    return int(np.clip((value / metric_def["scale_max"]) * 100, 0, 100))


def threshold_stops(metric_def):
    good, warn = metric_def["thresholds"]
    if not metric_def["lower_is_better"]:
        return "90%", "50%"
    return f"{np.clip((good / metric_def['scale_max']) * 100, 0, 100):.0f}%", f"{np.clip((warn / metric_def['scale_max']) * 100, 0, 100):.0f}%"


def build_metric_rows(result, metric_data, device, category, scope):
    rows = []
    for metric_def in METRIC_DEFINITIONS:
        key = metric_def["key"]
        reference_data, reference_label = get_reference_data(metric_data, key, device, category, scope)
        raw_value = clean_number(result.get(key))
        percentile = worse_percentile_for(reference_data, metric_def, raw_value)
        status, status_class = threshold_status(metric_def, raw_value)
        good_stop, warn_stop = threshold_stops(metric_def)
        rows.append(
            {
                "Area": metric_def["category"],
                "Metric": metric_def["label"],
                "Current value": format_value(raw_value, metric_def["unit"]),
                "Peer median": peer_median(reference_data, key, metric_def["unit"]),
                "Percentile vs peers": None if percentile is None else round(percentile),
                "Status": status,
                "status_class": status_class,
                "Status basis": metric_def["basis"],
                "Recommendation": metric_def["recommendation"],
                "resource_url": metric_def.get("resource_url"),
                "resource_label": metric_def.get("resource_label"),
                "key": key,
                "raw_value": raw_value,
                "unit": metric_def["unit"],
                "good_threshold": metric_def["thresholds"][0],
                "lower_is_better": metric_def["lower_is_better"],
                "short": metric_def["short"],
                "tier": metric_def["tier"],
                "marker_position": marker_position_for(metric_def, raw_value),
                "track_class": "score-track" if not metric_def["lower_is_better"] else "threshold-track",
                "track_style": f"--good-end: {good_stop}; --warn-end: {warn_stop};",
                "reference_label": reference_label,
            }
        )
    return rows


def build_field_metric_rows(result):
    rows = []
    for metric_def in FIELD_METRICS:
        raw_value = clean_number(result.get(metric_def["key"]))
        status, status_class = threshold_status(metric_def, raw_value)
        rows.append(
            {
                "Metric": metric_def["label"],
                "Current value": format_value(raw_value, metric_def["unit"]),
                "Status": status,
                "status_class": status_class,
                "Status basis": metric_def["basis"],
                "key": metric_def["key"],
                "raw_value": raw_value,
                "unit": metric_def["unit"],
                "good_threshold": metric_def["thresholds"][0],
                "lower_is_better": metric_def["lower_is_better"],
                "short": metric_def["short"],
            }
        )
    return rows


def issue_priority_score(issue):
    severity = {"Poor": 2, "Needs improvement": 1}.get(issue["Status"], 0)
    target = issue["good_threshold"]
    value = issue["raw_value"]
    distance = (value / target) if value is not None and target else 0
    is_field = issue["source"] == "Field"
    page_field = is_field and issue.get("field_data_scope") == "URL"
    is_core_web_vital = issue["short"] in {"LCP", "CLS", "INP"}
    return is_core_web_vital, page_field, severity, is_field, distance


def build_priority_issues(metric_rows, field_rows, field_scope=None):
    lab_by_key = {row["key"]: row for row in metric_rows}
    field_by_key = {row["key"]: row for row in field_rows}
    issues = []

    for issue_id, field_key, lab_key in PRIORITY_ISSUES:
        candidates = []
        for source, row in (("Field", field_by_key.get(field_key)), ("Lab", lab_by_key.get(lab_key))):
            if row and row["Status"] in {"Poor", "Needs improvement"}:
                candidates.append({
                    **row,
                    "issue_id": issue_id,
                    "source": source,
                    "field_data_scope": field_scope,
                    "lab_row": lab_by_key.get(lab_key),
                })
        if candidates:
            issues.append(max(candidates, key=issue_priority_score))

    return sorted(issues, key=issue_priority_score, reverse=True)


def priority_reason_for(issue):
    if issue["short"] == "TBT":
        return "First because no above-target Core Web Vital was found in the available results. This is a lab finding to investigate; missing results do not mean a pass."
    if issue["source"] == "Field" and issue.get("field_data_scope") == "URL":
        return "First because this page has an above-target real-user measurement; page-level visitor problems take priority."
    reason = "First among Core Web Vitals by severity, using real-user evidence to break ties, then distance above target. Core Web Vitals take priority over TBT."
    if issue["source"] == "Lab":
        return reason + " This is a lab finding to investigate."
    if issue.get("field_data_scope") == "Origin":
        return reason + " This website-wide finding needs checking on this page."
    return reason + " The real-user data's page or website scope is unavailable."


def strongest_positive_value(result, keys):
    values = [clean_number(result.get(key)) for key in keys]
    return max((value for value in values if value is not None and value > 0), default=None)


def fix_for_issue(issue, result):
    issue_id = issue["issue_id"]

    if issue_id == "lcp":
        server_latency = clean_number(result.get(
            "document-latency-insight_server_response_ms",
            result.get("network-server-latency"),
        ))
        # Investigate a slow first response before downstream loading work.
        if server_latency and server_latency > 800:
            return {
                "fix_id": "server",
                "title": "Ask about the slow first response",
                "evidence": f"PSI measured {format_value(server_latency, 'ms')} of server latency. Check this first because page loading waits for the initial response.",
                "url": "https://web.dev/articles/optimize-ttfb",
                "label": "server response guide",
            }

        render_savings = clean_number(result.get(
            "render-blocking-insight_lcp_savings_ms",
            result.get("render-blocking-resources_savings_ms"),
        ))
        if render_savings and render_savings > 0:
            return {
                "fix_id": "render_blocking",
                "title": "Check what delays the page appearing",
                "evidence": f"PSI estimates up to {format_value(render_savings, 'ms')} of potential savings.",
                "url": "https://developer.chrome.com/docs/performance/insights/render-blocking",
                "label": "technical render-blocking guide",
            }

        image_savings = clean_number(result.get(
            "image-delivery-insight_savings_bytes",
            strongest_positive_value(
                result,
                ("uses-responsive-images_savings_bytes", "uses-optimized-images_savings_bytes"),
            ),
        ))
        image = lcp_image_finding(result)
        if image and image_savings != 0:
            image_savings = image["savings_bytes"]
        if image_savings and image:
            return {
                "fix_id": "images",
                "title": "Make large images lighter to download",
                "evidence": f"PSI estimates up to {format_value(image_savings, 'bytes')} of potential transfer savings.",
                "url": "https://web.dev/learn/performance/image-performance",
                "label": "technical image guide",
            }

        if lcp_item(result) and lcp_item(result)["kind"] == "text":
            return {
                "fix_id": "lcp_text",
                "title": "Check why the main text appears late",
                "evidence": "The simulated test identified a text element as LCP. Identify what delayed it before changing images or fonts.",
                "url": "https://web.dev/articles/optimize-lcp",
                "label": "LCP optimization guide",
            }
        return {
            "fix_id": "lcp",
            "title": "Check the main image or heading",
            "evidence": "The main content took longer than the target to appear. This measurement does not identify the cause; start with the check above.",
            "url": "https://web.dev/articles/optimize-lcp",
            "label": "LCP optimization guide",
        }

    if issue_id == "cls":
        return {
            "fix_id": "cls",
            "title": "Find what makes the content move",
            "evidence": "Content moved more than the recommended limit. This measurement does not explain why.",
            "url": "https://web.dev/articles/optimize-cls",
            "label": "CLS optimization guide",
        }

    unused_javascript_bytes = clean_number(result.get("unused-javascript_savings_bytes"))
    unused_javascript_ms = clean_number(result.get("unused-javascript_savings_ms"))
    if unused_javascript_bytes or unused_javascript_ms:
        evidence = (
            f"The lab test found about {format_value(unused_javascript_bytes, 'bytes')} of code unused during this test. It may still be needed for other actions."
            if unused_javascript_bytes
            else f"PSI estimates up to {format_value(unused_javascript_ms, 'ms')} of potential savings."
        )
        return {
            "fix_id": "javascript",
            "title": "Review tools that add extra code",
            "evidence_group": "unused_scripts",
            "evidence": evidence,
            "url": "https://developer.chrome.com/docs/lighthouse/performance/unused-javascript",
            "label": "unused JavaScript guidance",
        }

    script_time = clean_number(result.get("mainthread_scriptEvaluation"))
    if script_time and script_time > 200:
        return {
            "fix_id": "javascript",
            "title": "Reduce work from apps and effects",
            "evidence_group": "script_work",
            "evidence": f"PSI measured {format_value(script_time, 'ms')} of script evaluation work.",
            "url": "https://web.dev/articles/optimize-long-tasks",
            "label": "long-task optimization guide",
        }

    return {
        "fix_id": "javascript",
        "title": "Check apps, popups, and interactive tools",
        "evidence": "The response or blocking measurement was above target. This measurement alone does not identify the responsible tool.",
        "url": "https://web.dev/articles/optimize-inp",
        "label": "INP optimization guide",
    }


def owner_guide_for(guidance):
    if not guidance["resource_url"]:
        return ""
    return (
        f'<a class="resource-link priority-link" href="{html.escape(guidance["resource_url"], quote=True)}" '
        f'target="_blank" rel="noopener">Follow these steps: {html.escape(guidance["resource_label"])}</a>'
    )


def render_platform_selector(result):
    detected_platform = result.get("detected_platform")
    if st.session_state.get("website_platform") not in PLATFORM_OPTIONS:
        st.session_state.website_platform = (
            detected_platform if detected_platform in PLATFORM_OPTIONS else "Other / Not sure"
        )

    platform = st.selectbox(
        "Your website platform",
        PLATFORM_OPTIONS,
        key="website_platform",
        help="Changing this updates the recommended actions only. It does not change the audit or benchmark results.",
    )
    platform_help = PLATFORM_HELP.get(platform)
    if platform_help:
        st.html(
            f'<div class="platform-help">'
            f'<a class="resource-link" href="{html.escape(platform_help["url"], quote=True)}" '
            f'target="_blank" rel="noopener">General {html.escape(platform)} performance guide</a>'
            '</div>'
        )
    if detected_platform in PLATFORM_OPTIONS:
        if platform == detected_platform:
            st.caption(
                f"Suggested from the audit: {detected_platform}. Change this if it is incorrect; only the instructions will update."
            )
        else:
            st.caption(
                f"The audit suggested {detected_platform}; using {platform} for the instructions. Audit results are unchanged."
            )
    else:
        st.caption(
            "The audit could not confidently identify the platform. Choose one to tailor the instructions; audit results are unchanged."
        )
    return platform


def issue_title_for(issue):
    if issue["issue_id"] == "lcp":
        return "Main content takes too long to appear"
    if issue["issue_id"] == "cls":
        return "Content moves unexpectedly" if issue["source"] == "Field" else "Content moves while the page loads"
    if issue["source"] == "Lab":
        return "The page may be slow to respond"
    return "Clicks and taps take too long to respond"


def visitor_impact_for(issue):
    impacts = {
        "lcp": "Visitors may wait longer to see the main image or text.",
        "cls": "Moving content can interrupt reading or make visitors tap the wrong link.",
        "responsiveness": "Visitors may notice a delay after clicking a button or tapping a menu.",
    }
    impact = impacts[issue["issue_id"]]
    if issue["source"] == "Lab":
        if issue["issue_id"] == "responsiveness":
            return "The test found work that could delay clicks and taps while loading. This is a warning sign, not a measurement of actual visitor response times."
        return impact + " This was found in a simulated test."
    if issue.get("field_data_scope") == "Origin":
        return impact + " The data covers this website overall; check whether this happens on this page."
    if issue.get("field_data_scope") != "URL":
        return impact + " We cannot tell whether the visitor data covers this page or the whole website."
    return impact


def lab_benchmark_context_for(issue):
    lab_row = issue.get("lab_row")
    if not lab_row or lab_row["Percentile vs peers"] is None:
        return "Lab benchmark position unavailable"
    return f"Lab result is worse than {lab_row['Percentile vs peers']:.0f}% of benchmark pages"


def target_text_for(row):
    direction = "or less" if row["lower_is_better"] else "or more"
    return f"Target: {format_value(row['good_threshold'], row['unit'])} {direction}"


def metric_title(row):
    if row["short"].lower() in row["Metric"].lower():
        return row["Metric"]
    return f"{row['Metric']} ({row['short']})"


def concise_target_for(row):
    comparison = "≤" if row["lower_is_better"] else "≥"
    return f"Target {comparison} {format_value(row['good_threshold'], row['unit'])}"


def render_data_source_header(title, context):
    st.markdown(
        f"""
        <div class="data-source-header">
            <div class="data-source-title">{html.escape(title)}</div>
            <div class="data-source-context">{html.escape(context)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def results_interpretation(lab_rows, field_rows, field_scope=None):
    areas = {"LCP": "loading speed", "CLS": "moving content", "INP": "click and tap response", "TBT": "response during loading"}
    problems = {
        "LCP": "the main content takes too long to appear",
        "CLS": "content moves more than it should as the page loads",
        "INP": "clicks and taps take too long to respond",
    }
    healthy = {
        "LCP": "Main content appears within the recommended time.",
        "CLS": "Content stays reasonably steady as the page loads.",
        "INP": "Clicks and taps respond within the recommended time.",
    }
    lab_available = [row for row in lab_rows if row["Status"] != "Unavailable"]
    field_available = [row for row in field_rows if row["Status"] != "Unavailable"]
    issue_statuses = {"Poor", "Needs improvement"}
    lab_issues = [row for row in lab_available if row["Status"] in issue_statuses]
    field_issues = [row for row in field_available if row["Status"] in issue_statuses]
    field_missing = [areas[key] for key in ("LCP", "CLS", "INP") if key not in {row["short"] for row in field_available}]
    lab_missing = [areas[key] for key in ("LCP", "CLS", "TBT") if key not in {row["short"] for row in lab_available}]

    if not lab_available and not field_available:
        return {
            "tone": "caution",
            "title": "There is not enough data to assess this page",
            "body": "No usable performance measurements were returned. Run another audit before choosing a fix.",
        }

    if not field_available:
        tone = "caution"
        title = "We only have a simulated test"
        condition = "found possible problems" if lab_issues else "met the recommended targets for the measurements available"
        body = f"The test {condition}. There is not enough real-user data to tell what visitors experience."
        if lab_issues:
            body += " Start with the checks below."
    else:
        scope = {"URL": " for this page", "Origin": " across this website"}.get(field_scope, "")
        if field_issues:
            tone = "poor"
            title = "Focus on " + " and ".join(areas[row["short"]] for row in field_issues)
            symptoms = " and ".join(problems[row["short"]] for row in field_issues)
            body = f"Real-user data{scope} shows that {symptoms}."
            body += " " + " ".join(healthy[row["short"]] for row in field_available if row["Status"] == "Good")
            body = body.rstrip()
        else:
            tone = "caution" if field_missing or field_scope != "URL" else ("mixed" if lab_issues else "good")
            title = "Some visitor results are missing" if field_missing else "The available visitor results look good"
            body = f"Real-user data{scope}: " + " ".join(healthy[row["short"]] for row in field_available)

        if field_scope == "Origin":
            body += " These results cover the whole website; they do not confirm how this particular page performs."
        elif field_scope != "URL":
            body += " We cannot tell whether these visitor results cover this page or the whole website."
        if field_missing:
            body += f" We do not have visitor results for: {', '.join(field_missing)}."
        if field_issues and field_scope == "URL":
            body += " Start with the fixes below for these visitor problems."
        elif lab_issues:
            body += " The simulated test also found possible problems. Use the checks below to investigate this page."
        elif field_issues:
            body += " Use the checks below to see whether these problems affect this page."

    if lab_missing:
        body += f" The simulated test has no result for: {', '.join(lab_missing)}."
    return {"tone": tone, "title": title, "body": body}


def render_results_interpretation(lab_rows, field_rows, field_scope=None):
    interpretation = results_interpretation(lab_rows, field_rows, field_scope)
    st.html(
        f"""
        <section class="meaning-card {interpretation['tone']}" aria-labelledby="results-meaning-title">
            <div class="meaning-label">What this means</div>
            <h3 class="meaning-title" id="results-meaning-title">{html.escape(interpretation['title'])}</h3>
            <p class="meaning-body">{html.escape(interpretation['body'])}</p>
        </section>
        """
    )


def render_metric_tile(row):
    st.markdown(
        f"""
        <div class="compact-metric">
            <div class="compact-label">{metric_title(row)}</div>
            <div class="compact-value {row['status_class']}">{row['Current value']}</div>
            <div class="compact-meta"><span class="{row['status_class']}">{row['Status']}</span> · {target_text_for(row)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_benchmark_card(row):
    percentile = row["Percentile vs peers"]
    percentile_label = "Unavailable" if percentile is None else f"{percentile:.0f}th peer percentile"
    headline = row["Status"]
    explanation = f"This marker shows the measured value on its threshold scale. Peer position: {percentile_label}."

    st.markdown(
        f"""
        <div class="benchmark-card {row['status_class']}">
            <div class="benchmark-header">
                <div>
                    <div class="benchmark-title">{row['Metric']}</div>
                    <p>{row['Area']} · {row['tier']}</p>
                </div>
                <div class="benchmark-percentile"><span class="{row['status_class']}">{headline}</span></div>
            </div>
            <div class="benchmark-track {row['track_class']}" style="{row['track_style']}">
                <div class="benchmark-marker" style="left: {row['marker_position']}%;"></div>
            </div>
            <div class="scale-labels"><span>{row['Status basis']}</span><span class="{row['status_class']}">{row['Current value']}</span></div>
            <p><span class="{row['status_class']}">{row['Status']}</span> - {explanation}</p>
            <div class="benchmark-meta">
                <div><span>This site</span>{row['Current value']}</div>
                <div><span>Peer median</span>{row['Peer median']}</div>
                <div><span>Peer position</span>{percentile_label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_benchmark_controls(metric_data, device):
    categories = available_categories(metric_data)
    all_pages_label = "All audited pages"
    comparison_group = st.selectbox(
        "Compare with",
        [all_pages_label, *categories],
        key="comparison_group",
        help="Changing the comparison updates the benchmark without rerunning the PSI audit.",
    )

    if comparison_group == all_pages_label:
        category = None
        comparison_scope = "All sites"
    else:
        category = comparison_group
        comparison_scope = "Selected category"

    reference_data, _ = get_reference_data(
        metric_data,
        "largest-contentful-paint",
        device,
        category,
        comparison_scope,
    )
    st.caption(f"Benchmark sample: {len(reference_data):,} {device} page audits")

    return category, comparison_scope


def item_label(item):
    if item["kind"] == "text":
        return f'Text: "{item["label"][:120]}"'
    if item.get("url"):
        parsed = urlsplit(item["url"])
        return (parsed.path.rsplit("/", 1)[-1] or parsed.hostname)[:120]
    return item["label"][:120]


def item_measurement(item):
    if "savings_bytes" in item:
        label = "estimated code unused during loading" if item["audit_id"] == "unused-javascript" else "estimated download reduction"
        return f"{label}: {format_value(item['savings_bytes'], 'bytes')}"
    if "cpu_ms" in item:
        return f"CPU work during loading: {format_value(item['cpu_ms'], 'ms')}"
    if "duration_ms" in item:
        return f"reported blocking duration: {format_value(item['duration_ms'], 'ms')}"
    if "shift_score" in item:
        return f"recorded shift score: {item['shift_score']:.3f} (one shift, not the page total)"
    return ""


def owner_finding_for(issue, result, fix):
    groups = result.get("audit_items", {})
    group = fix.get("evidence_group") or {"render_blocking": "render_blocking", "cls": "layout"}.get(fix["fix_id"])
    items = groups.get(group, [])
    item = next(iter(items), None)
    if fix["fix_id"] == "images":
        item = lcp_image_finding(result)
    if fix["fix_id"] in {"lcp", "lcp_text"}:
        item = lcp_item(result)
    if fix["fix_id"] == "cls":
        if not item:
            return "The results show a movement problem, but the test did not identify which part moved."
        label = " ".join(item.get("label", "").split())
        # Keep page text recognizable without exposing selectors or long resource names.
        if (not label or label in {item.get("selector"), item.get("url")}
                or label.lower() in {"div", "span", "img", "image", "video", "section", "main", "element"}
                or any(char in label for char in "<>/{}[]=#_")
                or max(map(len, label.split())) > 40):
            return ""
        if len(label) > 60 or len(label.split()) > 8:
            excerpt = " ".join(label.split()[:8])
            if len(excerpt) > 60:
                excerpt = excerpt[:60].rsplit(" ", 1)[0]
            return f'The simulated test recorded movement in an area labelled “{excerpt.rstrip(". …")}…”. Watch that area and anything appearing above it.'
        return f'The simulated test recorded movement around “{label}”. Watch whether it moves as other content appears.'
    if item:
        label = "Main content identified in the simulated test" if fix["fix_id"] in {"lcp", "lcp_text", "images"} else "Item identified in the simulated test"
        detail = item_measurement(item)
        return f"{label}: {item_label(item)}." + (f" {detail[0].upper() + detail[1:]}." if detail else "")
    if fix["fix_id"] == "server":
        return "Check the first response for the tested page with your hosting provider."
    if fix["fix_id"] == "render_blocking":
        return "The test found a possible delay from styles or scripts but did not identify a specific blocking file. Use the help request below."
    if fix["fix_id"] == "javascript":
        activity = {"unused_scripts": "unused code", "script_work": "script processing"}.get(group)
        if activity:
            return f"The test reported {activity} but did not identify a matching file. Use the help request below."
    if issue["issue_id"] == "lcp":
        return "The audit did not identify the main content. Run another test; if this repeats, use the help request below."
    return "The audit did not identify a specific item. Use the check above to investigate."


def render_recommendation_card(issue, result, platform, rank):
    fix = fix_for_issue(issue, result)
    guidance = guidance_for(platform, fix["fix_id"])
    owner_guide = owner_guide_for(guidance)
    finding = owner_finding_for(issue, result, fix)
    finding_html = f'<p class="audit-finding">{html.escape(finding)}</p>' if finding else ""
    is_primary = rank == 1
    css_class = "priority-card" if is_primary else "priority-card secondary-fix"
    source = "Lighthouse lab test"
    if issue["source"] == "Field":
        source = {
            "URL": "Real-user data for this page",
            "Origin": "Website-wide real-user data",
        }.get(issue.get("field_data_scope"), "Real-user data · Scope unavailable")
    if is_primary:
        eyebrow = f"Highest priority · {source}"
        peer_context = (
            f'<div class="priority-peer">{html.escape(priority_reason_for(issue))}</div>'
            f'<div class="priority-peer">{html.escape(lab_benchmark_context_for(issue))}</div>'
        )
    else:
        eyebrow = f"Priority {rank} · {source} · {issue['Status']}"
        peer_context = ""

    # These cards are HTML, not Markdown; optional sections must not become code blocks.
    st.html(
        f"""
        <article class="{css_class}" aria-label="Recommendation {rank}">
            <div class="priority-eyebrow {issue['status_class']}">{html.escape(eyebrow)}</div>
            <h4 class="priority-title">{html.escape(issue_title_for(issue))}</h4>
            <p class="priority-impact">{html.escape(visitor_impact_for(issue))}</p>
            <div class="priority-fix">
                <div class="priority-fix-label">Start with this</div>
                <div class="priority-fix-title">{html.escape(fix['title'])}</div>
                {finding_html}
                <p>{html.escape(guidance['owner_action'])}</p>
                {owner_guide}
            </div>
        </article>
        """
    )
    with st.container(key=f"owner_help_{issue['issue_id']}"):
        st.html(
            f'<div class="priority-help">'
            f'<div class="priority-fix-label">Prefer someone to fix it?</div>'
            f'<p>{html.escape(guidance["help_action"])}</p></div>'
        )
        with st.popover("Copy request for help", key=f"help_request_{issue['issue_id']}"):
            st.caption("Use the copy icon, then paste this into a message to your helper.")
            st.code(
                help_request_for(issue, result, platform, st.session_state.get("website"), st.session_state.get("strategy")),
                language=None, wrap_lines=True, height=320,
            )
    st.html(
        f"""
            <div class="fix-evidence">
                <strong>Supporting evidence</strong>
                <div class="priority-measurement">
                    <span>{html.escape(metric_title(issue))}:</span>
                    <span class="priority-value {issue['status_class']}">{html.escape(issue['Current value'])} · {html.escape(issue['Status'])}</span>
                    <span class="priority-target">{html.escape(concise_target_for(issue))}</span>
                </div>
                <p>{html.escape(fix['evidence'])}</p>
                {peer_context}
                <a class="resource-link" href="{html.escape(fix['url'], quote=True)}" target="_blank" rel="noopener">For your developer: {html.escape(fix['label'])}</a>
            </div>
        """
    )


def help_request_for(issue, result, platform, page_url, device):
    fix = fix_for_issue(issue, result)
    guidance = guidance_for(platform, fix["fix_id"])
    investigation = {
        "render_blocking": "Identify the CSS or scripts delaying the first render and LCP. Check which can be deferred or reduced without breaking the page.",
        "images": "Check image transfer sizes, responsive sizing, compression, and loading priority. Confirm which image, if any, is delaying LCP before changing it.",
        "server": "Investigate the initial server response, redirects, caching, and backend work. Confirm where the delay occurs before recommending hosting changes.",
        "lcp_text": "The reported LCP element is text. Investigate font loading and font-display, render-blocking CSS, server response, and client-side rendering. Confirm the delay before changing fonts or images.",
        "lcp": "Identify the LCP element and separate server delay, resource loading, and render delay to find what makes it appear late.",
        "cls": "Identify the elements causing layout shifts and when they move. Check image dimensions and space reserved for banners, embeds, or other late-loading content.",
        "javascript": "Profile long tasks and event handlers. Identify any app, plugin, third-party script, or theme code contributing to the delay before removing or deferring it. Code unused during one test may still be needed.",
    }[fix["fix_id"]]
    if fix.get("evidence_group") == "unused_scripts":
        investigation = "Identify which tools supply the reported unused JavaScript and whether that code can load only when needed. Check other pages and interactions before removing it; unused bytes do not establish processing time or an INP cause."
    elif fix.get("evidence_group") == "script_work":
        investigation = "Profile the scripts with reported CPU work during loading. Check long tasks and event handlers before deciding what to reduce or defer; loading work does not establish an INP cause."
    if issue["source"] == "Field":
        source = {
            "URL": "Real-user data for this page",
            "Origin": "Real-user data for the whole website, not this page alone",
        }.get(issue.get("field_data_scope"), "Real-user data; page-versus-website scope is unknown")
        source += "; previous 28 days; all devices"
    else:
        source = "Lighthouse simulated test"
    parts = [
        f"Please help investigate: {issue_title_for(issue)}.",
        f"Page: {page_url or '[page address unavailable]'}\nPlatform: {platform}\nSimulated test device: {device or '[device unavailable]'}",
        f"Observed result ({source}):\n{metric_title(issue)}: {issue['Current value']} ({issue['Status']}). {target_text_for(issue)}.",
    ]
    lab_row = issue.get("lab_row")
    if issue["source"] == "Field" and lab_row and lab_row["raw_value"] is not None:
        parts.append(f"Related Lighthouse result: {metric_title(lab_row)}: {lab_row['Current value']} ({lab_row['Status']}). {target_text_for(lab_row)}.")
    if issue["issue_id"] == "responsiveness":
        parts.append("TBT measures blocking during a simulated page load; it is not a measurement of real-user INP or proof of slow interactions.")
    parts.extend([
        f"Why this check was suggested: {fix['evidence']} These results do not confirm the root cause or guarantee an improvement.",
        f"Starting check: {owner_finding_for(issue, result, fix) or guidance['owner_action']}",
        f"Who to involve: {guidance['help_action']}",
        f"Please investigate: {investigation}",
        "Please report back with the confirmed cause, affected elements or resources, changes made (or proposed if work remains), and before-and-after results for the same page and simulated device. Check menus, forms, and checkout where present. If you cannot reproduce the problem, explain what you tested. Real-user results reflect 28 days and will not change immediately.",
        f"Technical reference: {fix['url']}",
    ])
    groups = result.get("audit_items", {})
    relevant = {"lcp": ("lcp", "render_blocking", "images"), "cls": ("layout",), "responsiveness": ("unused_scripts", "script_work")}[issue["issue_id"]]
    evidence = []
    for group in relevant:
        for item in groups.get(group, []):
            details = [item_label(item), item_measurement(item)]
            details.extend(f"{key}: {item[key]}" for key in ("url", "selector", "snippet") if item.get(key))
            evidence.append(f"- {group} [{item['audit_id']}]: " + "; ".join(value for value in details if value))
    if evidence:
        parts.append("Additional context from this simulated test (not element attribution from real-user data; not confirmed causes):\n" + "\n".join(evidence))
        parts.append("Image savings do not establish an LCP cause unless investigated; a moving element may not be the cause of a shift. Do not add overlapping savings together.")
    if issue["issue_id"] == "lcp" and not lcp_item(result):
        parts.append("The LCP element was not identified. Reproduce the page under comparable test conditions, inspect the loading timeline, and check which content was visible and eligible for LCP. Do not assume the hero image was measured.")
    return "\n\n".join(parts)


def render_action_plan(result, metric_rows, field_rows, platform, limit=3):
    issues = build_priority_issues(metric_rows, field_rows, result.get("field_data_scope"))[:limit]
    if not issues:
        st.info(
            "No above-target priority issues were found in the available measurements. "
            "Unavailable measurements are not a passing result."
        )
        return

    st.caption(
        "Start with one change. Save a backup or work on a draft before editing. "
        "If you are unsure how to undo a change, use the help route on the card."
    )
    for rank, issue in enumerate(issues, start=1):
        if rank == 2:
            st.markdown("#### Next priorities")
        with st.container(key=f"recommendation_{issue['issue_id']}"):
            render_recommendation_card(issue, result, platform, rank)

    st.markdown("#### Get help with these fixes")
    st.write(
        "Copy the request inside a recommendation and send it to the person named on the card. "
        "Use your hosting account, app or theme support page, or the agency that built your site."
    )
    support = PLATFORM_SUPPORT.get(platform)
    if support:
        st.html(
            f'<a class="resource-link" href="{html.escape(support["url"], quote=True)}" '
            f'target="_blank" rel="noopener">{html.escape(support["label"])}</a>'
        )
        st.caption(support["context"])
    else:
        st.caption("Not sure who runs your site? Check your website bill or editor login for the provider's name and support contact.")
    st.markdown("#### Check that the change helped")
    st.write(
        "Preview the page and check its menus, forms, and checkout if it has one. When the change is ready, publish it and run this audit again "
        "for the same page and device. Compare the lab measurement linked to the problem over a few runs, "
        "since single tests vary. If something stops working, undo the change. "
        "Real-user results cover the previous 28 days, so they will not update immediately."
    )


def render_overview(result, strategy, reference_label, metric_rows):
    if clean_number(result.get("largest-contentful-paint")) is None:
        st.warning("Loading speed could not be measured in the simulated test. Run another audit. Any available visitor results are shown separately below.")
    lab_rows = [
        row
        for row in metric_rows
        if row["key"] in {"largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time"}
    ]
    field_rows = build_field_metric_rows(result)
    field_scope = result.get("field_data_scope")

    render_data_source_header(
        "Lab data",
        f"Controlled test · Simulated {strategy.lower()} · Benchmark: {reference_label}",
    )
    lab_cols = st.columns(3)
    for col, row in zip(lab_cols, lab_rows):
        with col:
            render_metric_tile(row)

    st.markdown('<div class="metric-section-divider"></div>', unsafe_allow_html=True)
    if field_scope == "URL":
        field_context = "Real-user experience · This page · Previous 28 days · All devices"
    elif field_scope == "Origin":
        field_context = "Real-user experience · Website-wide (origin fallback) · Previous 28 days · All devices"
    elif any(row["Status"] != "Unavailable" for row in field_rows):
        field_context = "Real-user experience · Scope unavailable · Previous 28 days · All devices"
    else:
        field_context = "Real-user experience · CrUX unavailable for this URL and origin"
    render_data_source_header("Field data", field_context)
    field_cols = st.columns(3)
    for col, row in zip(field_cols, field_rows):
        with col:
            render_metric_tile(row)

    render_results_interpretation(lab_rows, field_rows, field_scope)
    st.html('<h2 class="recommendations-heading">What to Fix First</h2>')
    platform = render_platform_selector(result)
    render_action_plan(result, metric_rows, field_rows, platform, limit=3)


def render_benchmark(metric_rows, reference_label):
    st.subheader("Metric Details")
    st.caption(f"Comparison set: {reference_label}. Open a row to see thresholds, peer median, and benchmark position.")

    lab_rows = [row for row in metric_rows if row["key"] not in FIELD_DATA_KEYS]
    field_rows = [row for row in metric_rows if row["key"] in FIELD_DATA_KEYS]

    st.markdown("#### Lab benchmark details")
    st.caption("Metrics from the current simulated Lighthouse run.")
    for row in [row for row in lab_rows if row["tier"] == "Core Web Vital"]:
        render_benchmark_card(row)

    st.markdown("##### Supporting lab metrics")
    secondary_rows = [row for row in lab_rows if row["tier"] != "Core Web Vital"]
    for row in secondary_rows:
        label = f"{metric_title(row)} · {row['Current value']} · {row['Status']}"
        with st.expander(label, expanded=False):
            render_benchmark_card(row)

    st.markdown("#### Field benchmark details")
    st.caption("Real-user CrUX metrics, kept separate from the simulated lab run.")
    for row in field_rows:
        render_benchmark_card(row)

    display_rows = [
        {"Source": "Field" if row["key"] in FIELD_DATA_KEYS else "Lab", **row}
        for row in metric_rows
    ]
    display_df = pd.DataFrame(display_rows).drop(
        columns=[
            "key", "raw_value", "unit", "good_threshold", "lower_is_better", "short",
            "status_class", "marker_position", "track_class", "track_style",
        ]
    )
    st.dataframe(display_df, width="stretch", hide_index=True)


def render_raw_audit(result):
    st.caption("Advanced view of the extracted PageSpeed Insights fields used by the dashboard.")
    rows = [{"Field": key, "Value": value} for key, value in sorted(result.items())]
    display_df = pd.DataFrame(rows, columns=["Field", "Value"]).astype({"Value": "string"})
    st.dataframe(display_df, width="stretch", hide_index=True)


def load_component(metric_data, category=None, scope=None):
    """Render results; category and scope remain optional for safe Streamlit hot reloads."""
    result = st.session_state.result
    strategy = st.session_state.strategy
    device = strategy.lower()

    _, overview_reference_label = get_reference_data(
        metric_data, "largest-contentful-paint", device, None, "All sites"
    )
    overview_rows = build_metric_rows(result, metric_data, device, None, "All sites")

    tabs = st.tabs(["Overview", "Detailed results"])
    with tabs[0]:
        render_overview(result, strategy, overview_reference_label, overview_rows)
    with tabs[1]:
        category, comparison_scope = render_benchmark_controls(metric_data, device)
        _, detail_reference_label = get_reference_data(
            metric_data,
            "largest-contentful-paint",
            device,
            category,
            comparison_scope,
        )
        detail_rows = (
            overview_rows
            if category is None
            else build_metric_rows(result, metric_data, device, category, comparison_scope)
        )
        render_benchmark(detail_rows, detail_reference_label)
        with st.expander("Advanced: raw audit data", expanded=False):
            render_raw_audit(result)
