import html
import math

import numpy as np
import pandas as pd
import streamlit as st

from utils.platform_guidance import PLATFORM_HELP, PLATFORM_OPTIONS, guidance_for


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
    {
        "label": "Largest Contentful Paint",
        "key": "field_largest-contentful-paint",
        "short": "LCP",
        "unit": "ms",
        "lower_is_better": True,
        "thresholds": (2500, 4000),
        "basis": "Core Web Vitals: good <= 2.5s, needs improvement <= 4.0s, poor > 4.0s.",
    },
    {
        "label": "Cumulative Layout Shift",
        "key": "field_cumulative-layout-shift",
        "short": "CLS",
        "unit": "score",
        "lower_is_better": True,
        "thresholds": (0.1, 0.25),
        "basis": "Core Web Vitals: good <= 0.10, needs improvement <= 0.25, poor > 0.25.",
    },
    {
        "label": "Interaction to Next Paint",
        "key": "INTERACTION_TO_NEXT_PAINT",
        "short": "INP",
        "unit": "ms",
        "lower_is_better": True,
        "thresholds": (200, 500),
        "basis": "Core Web Vitals: good <= 200ms, needs improvement <= 500ms, poor > 500ms.",
    },
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

SCENARIO_METRICS = [
    {"label": "Unused JavaScript", "key": "unused-javascript"},
    {"label": "Total Byte Weight", "key": "total-byte-weight"},
    {"label": "Image Bytes", "key": "resource_image_bytes"},
    {"label": "Font Bytes", "key": "resource_font_bytes"},
    {"label": "Unused CSS Rules", "key": "unused-css-rules"},
    {"label": "Unused JavaScript Savings", "key": "unused-javascript_savings_bytes"},
    {"label": "Third-Party Bytes", "key": "resource_third-party_bytes"},
]


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
            div[data-testid="stMetric"], .benchmark-card {
                background: #1f2937 !important;
                border: 1px solid #334155;
                border-radius: 8px;
                box-shadow: none;
            }
            div[data-testid="stMetric"] {padding: 14px 16px;}
            div[data-testid="stMetric"] * {color: #f8fafc !important;}
            div[data-testid="stMetricLabel"] p {font-size: 0.86rem; color: #cbd5e1 !important;}
            div[data-testid="stMetricValue"] {font-size: 1.55rem;}
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
            .overview-recs {margin-top: 10px;}
            .priority-card {background: #1f2937; border: 1px solid #475569; border-radius: 8px; padding: 20px 22px; margin-bottom: 18px;}
            .priority-eyebrow {font-size: 0.75rem; font-weight: 850; letter-spacing: 0.08em; text-transform: uppercase;}
            .priority-eyebrow.status-good {color: #34d399 !important;}
            .priority-eyebrow.status-watch {color: #fbbf24 !important;}
            .priority-eyebrow.status-poor {color: #f87171 !important;}
            .priority-title {font-size: 1.2rem; font-weight: 800; color: #f8fafc !important; margin: 4px 0 10px;}
            .priority-measurement {display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px 14px;}
            .priority-value {font-size: 2.5rem; line-height: 1; font-weight: 850;}
            .priority-value.status-good {color: #34d399 !important;}
            .priority-value.status-watch {color: #fbbf24 !important;}
            .priority-value.status-poor {color: #f87171 !important;}
            .priority-target {font-size: 0.9rem; color: #cbd5e1 !important;}
            .priority-impact {font-size: 1rem; font-weight: 800; margin-top: 8px;}
            .priority-impact.status-good {color: #34d399 !important;}
            .priority-impact.status-watch {color: #fbbf24 !important;}
            .priority-impact.status-poor {color: #f87171 !important;}
            .priority-peer {font-size: 0.8rem; color: #94a3b8 !important; margin-top: 2px;}
            .priority-fix {background: #273449; border-left: 3px solid #60a5fa; border-radius: 5px; padding: 12px 14px; margin-top: 14px;}
            .priority-fix-label {font-size: 0.7rem; font-weight: 850; letter-spacing: 0.07em; text-transform: uppercase; color: #93c5fd !important;}
            .priority-fix-title {font-size: 1rem; font-weight: 800; color: #f8fafc !important; margin-top: 2px;}
            .priority-fix p {margin: 5px 0 0; color: #cbd5e1 !important; line-height: 1.45;}
            .priority-help {border-top: 1px solid #475569; margin-top: 12px; padding-top: 12px;}
            .fix-evidence {font-size: 0.78rem; color: #94a3b8 !important; margin-top: 5px;}
            .resource-links {display: flex; flex-wrap: wrap; align-items: flex-start; gap: 8px 10px;}
            .resource-link.priority-link {border-color: #60a5fa;}
            .priority-card.secondary-fix {padding: 18px 20px; border-color: #334155;}
            .secondary-fix .priority-title {font-size: 1.1rem;}
            .secondary-fix .priority-value {font-size: 2rem;}
            .resource-link {display: inline-flex; align-items: center; box-sizing: border-box; max-width: 100%; min-height: 44px; padding: 9px 12px; border: 1px solid #64748b; border-radius: 6px; margin-top: 10px; color: #93c5fd !important; font-weight: 700; text-decoration: none; overflow-wrap: anywhere;}
            .resource-link:hover {background: #334155; text-decoration: underline;}
            .resource-link:focus-visible {outline: 2px solid #93c5fd; outline-offset: 3px;}
            .platform-help .resource-link {margin-top: 0; font-size: 0.875rem; font-weight: 600;}
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
    if math.isnan(numeric) or math.isinf(numeric):
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
    field_priority = 1 if issue["source"] == "Field" else 0
    return severity, field_priority, distance


def build_priority_issues(metric_rows, field_rows):
    lab_by_key = {row["key"]: row for row in metric_rows}
    field_by_key = {row["key"]: row for row in field_rows}
    issues = []

    for issue_id, field_key, lab_key in PRIORITY_ISSUES:
        field_row = field_by_key.get(field_key)
        lab_row = lab_by_key.get(lab_key)
        if field_row and field_row["Status"] in {"Poor", "Needs improvement"}:
            measured_row = field_row
            source = "Field"
        elif lab_row and lab_row["Status"] in {"Poor", "Needs improvement"}:
            measured_row = lab_row
            source = "Lab"
        else:
            continue

        issue = dict(measured_row)
        issue["issue_id"] = issue_id
        issue["source"] = source
        issue["lab_row"] = lab_row
        issues.append(issue)

    issues.sort(key=issue_priority_score, reverse=True)
    return issues


def strongest_positive_value(result, keys):
    values = [clean_number(result.get(key)) for key in keys]
    return max((value for value in values if value is not None and value > 0), default=None)


def fix_for_issue(issue, result):
    issue_id = issue["issue_id"]

    if issue_id == "lcp":
        render_savings = clean_number(result.get("render-blocking-resources_savings_ms"))
        if render_savings and render_savings > 0:
            return {
                "fix_id": "render_blocking",
                "title": "Remove render-blocking resources",
                "evidence": f"PSI estimates up to {format_value(render_savings, 'ms')} of potential savings.",
                "url": "https://developer.chrome.com/docs/performance/insights/render-blocking",
                "label": "technical render-blocking guide",
            }

        image_savings = strongest_positive_value(
            result,
            ("uses-responsive-images_savings_bytes", "uses-optimized-images_savings_bytes"),
        )
        if image_savings:
            return {
                "fix_id": "images",
                "title": "Optimize image delivery",
                "evidence": f"PSI estimates up to {format_value(image_savings, 'bytes')} of potential transfer savings.",
                "url": "https://web.dev/learn/performance/image-performance",
                "label": "technical image guide",
            }

        server_latency = clean_number(result.get("network-server-latency"))
        if server_latency and server_latency > 800:
            return {
                "fix_id": "server",
                "title": "Improve the initial server response",
                "evidence": f"PSI measured {format_value(server_latency, 'ms')} of server latency.",
                "url": "https://web.dev/articles/optimize-ttfb",
                "label": "server response guide",
            }

        return {
            "fix_id": "lcp",
            "title": "Inspect and optimize the LCP element",
            "evidence": "Recommended from the failing LCP measurement; no larger PSI savings estimate was available.",
            "url": "https://web.dev/articles/optimize-lcp",
            "label": "LCP optimization guide",
        }

    if issue_id == "cls":
        return {
            "fix_id": "cls",
            "title": "Reserve space for elements that shift",
            "evidence": "Recommended from the failing CLS measurement.",
            "url": "https://web.dev/articles/optimize-cls",
            "label": "CLS optimization guide",
        }

    unused_javascript_bytes = clean_number(result.get("unused-javascript_savings_bytes"))
    unused_javascript_ms = clean_number(result.get("unused-javascript_savings_ms"))
    if unused_javascript_bytes or unused_javascript_ms:
        evidence = (
            f"PSI estimates about {format_value(unused_javascript_bytes, 'bytes')} of removable code."
            if unused_javascript_bytes
            else f"PSI estimates up to {format_value(unused_javascript_ms, 'ms')} of potential savings."
        )
        return {
            "fix_id": "javascript",
            "title": "Reduce unused JavaScript",
            "evidence": evidence,
            "url": "https://developer.chrome.com/docs/lighthouse/performance/unused-javascript",
            "label": "unused JavaScript guidance",
        }

    script_time = clean_number(result.get("mainthread_scriptEvaluation"))
    if script_time and script_time > 200:
        return {
            "fix_id": "javascript",
            "title": "Break up JavaScript execution",
            "evidence": f"PSI measured {format_value(script_time, 'ms')} of script evaluation work.",
            "url": "https://web.dev/articles/optimize-long-tasks",
            "label": "long-task optimization guide",
        }

    return {
        "fix_id": "javascript",
        "title": "Investigate long main-thread tasks",
        "evidence": "Recommended from the failing INP or TBT measurement.",
        "url": "https://web.dev/articles/optimize-inp",
        "label": "INP optimization guide",
    }


def resource_links_for(fix, guidance):
    links = []
    if guidance["resource_url"]:
        links.append(
            f'<a class="resource-link priority-link" href="{html.escape(guidance["resource_url"], quote=True)}" '
            f'target="_blank" rel="noopener">Follow these steps: {html.escape(guidance["resource_label"])}</a>'
        )
    links.append(
        f'<a class="resource-link" href="{html.escape(fix["url"], quote=True)}" '
        f'target="_blank" rel="noopener">For your developer: {html.escape(fix["label"])}</a>'
    )
    return f'<div class="resource-links">{"".join(links)}</div>'


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
    if issue["issue_id"] == "responsiveness" and issue["source"] == "Lab":
        return "Responsiveness risk (TBT)"
    return metric_title(issue)


def lab_benchmark_context_for(issue):
    lab_row = issue.get("lab_row")
    if not lab_row or lab_row["Percentile vs peers"] is None:
        return "Lab benchmark position unavailable"
    return f"Lab result is worse than {lab_row['Percentile vs peers']:.0f}% of benchmark pages"


def target_text_for(row):
    metric_targets = {
        "largest-contentful-paint": "Target: 2.5s or less",
        "field_largest-contentful-paint": "Target: 2.5s or less",
        "cumulative-layout-shift": "Target: 0.10 or less",
        "field_cumulative-layout-shift": "Target: 0.10 or less",
        "INTERACTION_TO_NEXT_PAINT": "Target: 200ms or less",
    }
    return metric_targets.get(row["key"], row["Status basis"])


def metric_title(row):
    if row["short"].lower() in row["Metric"].lower():
        return row["Metric"]
    return f"{row['Metric']} ({row['short']})"


def concise_target_for(row):
    comparison = "≤" if row["lower_is_better"] else "≥"
    return f"Target {comparison} {format_value(row['good_threshold'], row['unit'])}"


def impact_text_for(row):
    value = row["raw_value"]
    target = row["good_threshold"]
    if value is None or not target:
        return row["Status"]
    if row["lower_is_better"] and value > target:
        qualifier = "slower" if row["unit"] == "ms" else "above"
        return f"{value / target:.1f}× {qualifier} than the healthy target"
    if not row["lower_is_better"] and value < target:
        if row["unit"] == "score_percent":
            return f"{(target - value) * 100:.0f} points below the healthy target"
        return "Below the healthy target"
    return "Within the healthy target"


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

    reference_key = f"{device}|{category}|{comparison_scope}"
    if st.session_state.get("reference_key") != reference_key:
        st.session_state.reference_key = reference_key
        st.session_state.pop("estimated_new_lcp", None)
        st.session_state.pop("percent_improvement", None)

    return category, comparison_scope


def render_recommendation_card(issue, result, platform, rank):
    fix = fix_for_issue(issue, result)
    guidance = guidance_for(platform, fix["fix_id"])
    resource_links = resource_links_for(fix, guidance)
    is_primary = rank == 1
    css_class = "priority-card" if is_primary else "priority-card secondary-fix"
    if is_primary:
        source = "Real-user field data" if issue["source"] == "Field" else "Current Lighthouse lab test"
        eyebrow = f"Highest priority · {source}"
        peer_context = f'<div class="priority-peer">{html.escape(lab_benchmark_context_for(issue))}</div>'
    else:
        source = "Field data" if issue["source"] == "Field" else "Lab test"
        eyebrow = f"Priority {rank} · {source} · {issue['Status']}"
        peer_context = ""

    # These cards are HTML, not Markdown; optional sections must not become code blocks.
    st.html(
        f"""
        <article class="{css_class}" aria-label="Recommendation {rank}">
            <div class="priority-eyebrow {issue['status_class']}">{html.escape(eyebrow)}</div>
            <h4 class="priority-title">{html.escape(issue_title_for(issue))}</h4>
            <div class="priority-measurement">
                <span class="priority-value {issue['status_class']}">{html.escape(issue['Current value'])}</span>
                <span class="priority-target">{html.escape(concise_target_for(issue))}</span>
            </div>
            <div class="priority-impact {issue['status_class']}">{html.escape(impact_text_for(issue))}</div>
            {peer_context}
            <div class="priority-fix">
                <div class="priority-fix-label">What you can try</div>
                <div class="priority-fix-title">{html.escape(fix['title'])}</div>
                <p>{html.escape(guidance['owner_action'])}</p>
                <div class="priority-help">
                    <div class="priority-fix-label">When to get help</div>
                    <p>{html.escape(guidance['help_action'])}</p>
                </div>
                <div class="fix-evidence"><strong>Why this was suggested:</strong> {html.escape(fix['evidence'])}</div>
            </div>
            {resource_links}
        </article>
        """
    )


def render_action_plan(result, metric_rows, field_rows, platform, limit=3):
    issues = build_priority_issues(metric_rows, field_rows)[:limit]
    if not issues:
        st.info(
            "No above-target priority issues were found in the available measurements. "
            "Unavailable measurements are not a passing result."
        )
        return

    for rank, issue in enumerate(issues, start=1):
        if rank == 2:
            st.markdown("#### Next priorities")
            st.caption("Start with the highest priority above, then work through these actions.")
        render_recommendation_card(issue, result, platform, rank)


def render_overview(result, strategy, reference_label, metric_rows):
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
        field_context = "Real-user experience · Previous 28 days · All devices"
    elif field_scope == "Origin":
        field_context = "Real-user experience · Origin-level fallback · Previous 28 days · All devices"
    else:
        field_context = "Real-user experience · CrUX unavailable for this URL and origin"
    render_data_source_header("Field data", field_context)
    field_cols = st.columns(3)
    for col, row in zip(field_cols, field_rows):
        with col:
            render_metric_tile(row)

    st.markdown('<div class="overview-recs">', unsafe_allow_html=True)
    st.subheader("What to Fix First")
    platform = render_platform_selector(result)
    render_action_plan(result, metric_rows, field_rows, platform, limit=3)
    st.markdown("</div>", unsafe_allow_html=True)


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


def percentile_for(reference_data, metric, value):
    value = clean_number(value)
    if value is None or metric not in reference_data.columns:
        return None
    series = pd.to_numeric(reference_data[metric], errors="coerce").dropna()
    if series.empty:
        return None
    values = series.to_numpy(dtype=float)
    lower_count = np.sum(values < value)
    equal_count = np.sum(values == value)
    percentile = ((lower_count + (0.5 * equal_count)) / len(values)) * 100
    return float(np.clip(percentile, 0, 100))


def render_scenario_planner(result, device, lcp_reference_data, pred_value):
    from utils.predict import predict

    st.subheader("What-if Improvement Planner")
    st.caption("Explore how LCP might change if resource issues moved closer to better-performing peers. This is a planning estimate, not a guaranteed PSI result.")

    col1, col2 = st.columns(2)
    col1.metric("Current measured LCP", format_value(result.get("largest-contentful-paint"), "ms"))
    if st.session_state.get("estimated_new_lcp") is not None:
        col2.metric("Scenario LCP estimate", format_value(st.session_state.estimated_new_lcp, "ms"), delta=f"{st.session_state.percent_improvement:.1f}% lower")
    else:
        col2.metric("Scenario LCP estimate", "Not calculated")

    if pred_value is None:
        st.warning("The model could not create a baseline prediction for this audit, so the what-if planner is unavailable.")
        return

    with st.form("optimization_form"):
        st.write("Choose target peer percentiles for the resource areas you might improve.")
        reset_changes = st.form_submit_button("Reset Planner")
        if reset_changes:
            for metric in SCENARIO_METRICS:
                original_percentile = percentile_for(lcp_reference_data, metric["key"], result.get(metric["key"]))
                st.session_state[f"{device}_{metric['key']}"] = int(original_percentile or 50)
            st.session_state.pop("estimated_new_lcp", None)
            st.session_state.pop("percent_improvement", None)
            st.rerun()

        selected_percentiles = {}
        original_percentiles = {}
        col_a, col_b = st.columns(2)
        for index, metric in enumerate(SCENARIO_METRICS):
            key = metric["key"]
            start_percentile = int(round(percentile_for(lcp_reference_data, key, result.get(key)) or 50))
            original_percentiles[key] = start_percentile
            column = col_a if index % 2 == 0 else col_b
            with column:
                selected_percentiles[key] = st.slider(
                    metric["label"],
                    min_value=0,
                    max_value=100,
                    value=start_percentile,
                    key=f"{device}_{st.session_state.reference_key}_{key}",
                    help="Lower targets represent lighter, faster peer behavior. Leaving the slider unchanged keeps the original audit value.",
                )
        submitted = st.form_submit_button("Estimate What-if Result")

    if submitted:
        modified_result = result.copy()
        changed_metrics = 0
        for metric, percentile in selected_percentiles.items():
            if percentile == original_percentiles.get(metric):
                continue
            series = pd.to_numeric(lcp_reference_data[metric], errors="coerce").dropna()
            if not series.empty:
                modified_result[metric] = np.percentile(series, percentile)
                changed_metrics += 1

        if changed_metrics == 0:
            st.session_state.percent_improvement = 0.0
            st.session_state.estimated_new_lcp = result["largest-contentful-paint"]
            st.rerun()

        new_prediction = predict(modified_result, device)
        if new_prediction is None:
            st.warning("The model could not estimate that scenario because required audit fields were unavailable.")
            return

        new_pred_value = float(new_prediction[0])
        if pred_value <= 0:
            st.warning("The baseline prediction was not valid, so the scenario estimate could not be calculated.")
            return

        percent_improvement = ((pred_value - new_pred_value) / pred_value) * 100
        estimated_new_lcp = result["largest-contentful-paint"] * (new_pred_value / pred_value)
        st.session_state.percent_improvement = percent_improvement
        st.session_state.estimated_new_lcp = estimated_new_lcp
        st.rerun()


def render_raw_audit(result):
    st.subheader("Raw Audit Data")
    st.caption("Advanced view of the extracted PageSpeed Insights fields used by the dashboard.")
    rows = [{"Field": key, "Value": value} for key, value in sorted(result.items())]
    display_df = pd.DataFrame(rows, columns=["Field", "Value"]).astype({"Value": "string"})
    st.dataframe(display_df, width="stretch", hide_index=True)


def load_component(metric_data, category, scope):
    result = st.session_state.result
    strategy = st.session_state.strategy
    device = strategy.lower()

    _, reference_label = get_reference_data(metric_data, "largest-contentful-paint", device, category, scope)
    metric_rows = build_metric_rows(result, metric_data, device, category, scope)

    tabs = st.tabs(["Overview", "Metric Details", "Raw Audit Data"])
    with tabs[0]:
        render_overview(result, strategy, reference_label, metric_rows)
    with tabs[1]:
        render_benchmark(metric_rows, reference_label)
    with tabs[2]:
        render_raw_audit(result)


















