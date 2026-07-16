import math

import numpy as np
import pandas as pd
import streamlit as st

from utils.predict import predict


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
            div[data-testid="stMetric"], .metric-tile, .benchmark-card, .recommendation-card {
                background: #1f2937 !important;
                border: 1px solid #334155;
                border-radius: 8px;
                box-shadow: none;
            }
            div[data-testid="stMetric"] {padding: 14px 16px;}
            div[data-testid="stMetric"] * {color: #f8fafc !important;}
            div[data-testid="stMetricLabel"] p {font-size: 0.86rem; color: #cbd5e1 !important;}
            div[data-testid="stMetricValue"] {font-size: 1.55rem;}
            .metric-tile {padding: 18px 20px; min-height: 150px;}
            .metric-tile h4, .benchmark-card h4, .recommendation-card h4 {margin: 0 0 8px 0; color: #f8fafc !important;}
            .metric-value {font-size: 2rem; line-height: 1.1; font-weight: 800; color: #f8fafc !important; margin-bottom: 10px;}
            .metric-meta, .metric-tile p, .benchmark-card p, .recommendation-card p {margin: 0; color: #cbd5e1 !important; line-height: 1.5;}
            .status-good {color: #34d399 !important; font-weight: 750;}
            .status-watch {color: #fbbf24 !important; font-weight: 750;}
            .status-poor {color: #f87171 !important; font-weight: 750;}
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
            .benchmark-meta {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px;}
            .benchmark-meta div {background: #273449; border-radius: 6px; padding: 8px 10px; color: #f8fafc !important;}
            .benchmark-meta span {display: block; color: #cbd5e1 !important; font-size: 0.78rem;}
            .recommendation-card {padding: 18px 20px; margin-bottom: 14px;}
            .recommendation-card h4 {font-size: 1.05rem;}
            .recommendation-meta {margin-bottom: 8px !important; color: #cbd5e1 !important;}
            .overview-recs {margin-top: 22px;}`r`n            .action-grid {display: grid; grid-template-columns: 1.25fr 1fr; gap: 14px; margin-top: 10px;}`r`n            .action-card-primary {border-color: #475569; background: #243244 !important;}`r`n            .resource-link {display: inline-block; margin-top: 10px; color: #93c5fd !important; font-weight: 700; text-decoration: none;}`r`n            .resource-link:hover {text-decoration: underline;}
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
    data = pd.concat(metric_data["largest-contentful-paint"].values(), ignore_index=True)
    return sorted(category for category in data["category"].dropna().unique() if category != "null")


def get_reference_data(metric_data, metric, device, category, scope):
    reference_data = metric_data[metric][device].copy()
    if scope == "Selected category":
        scoped = reference_data[reference_data["category"] == category].copy()
        if len(scoped) >= 20:
            return scoped, f"{category} {device} sites"
        return reference_data, f"all {device} sites; selected category sample was too small"
    return reference_data, f"all {device} sites"


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
    if metric_def["lower_is_better"]:
        return int(np.clip((value / metric_def["scale_max"]) * 100, 0, 100))
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
                "short": metric_def["short"],
                "tier": metric_def["tier"],
                "marker_position": marker_position_for(metric_def, raw_value),
                "track_class": "score-track" if not metric_def["lower_is_better"] else "threshold-track",
                "track_style": f"--good-end: {good_stop}; --warn-end: {warn_stop};",
                "reference_label": reference_label,
            }
        )
    return rows


def priority_score(row):
    percentile = row["Percentile vs peers"]
    if percentile is None:
        return -1
    status_boost = {"Poor": 200, "Needs improvement": 100, "Good": 0}.get(row["Status"], 0)
    return status_boost + percentile


def top_opportunities(metric_rows, limit=4):
    ranked = [row for row in metric_rows if row["Status"] != "Good"]
    ranked.sort(key=priority_score, reverse=True)
    return ranked[:limit]



def target_text_for(row):
    metric_targets = {
        "largest-contentful-paint": "Target: 2.5s or less",
        "cumulative-layout-shift": "Target: 0.10 or less",
        "INTERACTION_TO_NEXT_PAINT": "Target: 200ms or less",
    }
    return metric_targets.get(row["key"], row["Status basis"])


def metric_title(row):
    return f"{row['Metric']} ({row['short']})"
def render_metric_tile(row):
    st.markdown(
        f"""
        <div class="metric-tile">
            <h4>{metric_title(row)}</h4>
            <div class="metric-value">{row['Current value']}</div>
            <p class="metric-meta">{target_text_for(row)}</p>
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
        <div class="benchmark-card">
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
            <div class="scale-labels"><span>{row['Status basis']}</span><span>{row['Current value']}</span></div>
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
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = categories[0]
    if "comparison_scope" not in st.session_state:
        st.session_state.comparison_scope = "All sites"

    st.subheader("Comparison Settings")
    control_col1, control_col2 = st.columns([1, 2])
    with control_col1:
        comparison_scope = st.radio("Benchmark group", ["All sites", "Selected category"], key="comparison_scope")
    with control_col2:
        selected_category = st.selectbox(
            "Compare against category",
            categories,
            key="selected_category",
            help="Only applies when Benchmark group is set to Selected category. The PSI result stays saved; only the benchmark group changes.",
            disabled=st.session_state.comparison_scope == "All sites",
        )

    reference_key = f"{device}|{selected_category}|{comparison_scope}"
    if st.session_state.get("reference_key") != reference_key:
        st.session_state.reference_key = reference_key
        st.session_state.pop("estimated_new_lcp", None)
        st.session_state.pop("percent_improvement", None)

    return selected_category, comparison_scope


def render_action_plan(metric_rows, limit=3):
    priorities = top_opportunities(metric_rows, limit=limit)
    if not priorities:
        st.info("The main PageSpeed metrics are within their target ranges for this audit.")
        return

    primary = priorities[0]
    supporting = priorities[1:]
    resource_url = primary.get("resource_url") or "https://web.dev/learn/performance"
    resource_label = primary.get("resource_label") or "web.dev performance guide"
    peer_text = "peer percentile unavailable" if primary["Percentile vs peers"] is None else f"{primary['Percentile vs peers']:.0f}th peer percentile"

    st.markdown(
        f"""
        <div class="recommendation-card action-card-primary">
            <h4>Fix first: {metric_title(primary)}</h4>
            <p class="recommendation-meta"><span class="{primary['status_class']}">{primary['Status']}</span> · {primary['Current value']} now · target {target_text_for(primary).replace('Target: ', '')} · {peer_text}</p>
            <p>{primary['Recommendation']}</p>
            <a class="resource-link" href="{resource_url}" target="_blank">Open {resource_label}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if supporting:
        st.markdown("#### Also check")
        for row in supporting:
            row_resource_url = row.get("resource_url") or "https://web.dev/learn/performance"
            row_resource_label = row.get("resource_label") or "web.dev performance guide"
            st.markdown(
                f"""
                <div class="recommendation-card">
                    <h4>{metric_title(row)}</h4>
                    <p class="recommendation-meta"><span class="{row['status_class']}">{row['Status']}</span> · {row['Current value']} now · target {target_text_for(row).replace('Target: ', '')}</p>
                    <p>{row['Recommendation']}</p>
                    <a class="resource-link" href="{row_resource_url}" target="_blank">Open {row_resource_label}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )



def render_result_summary(metric_rows):
    priorities = top_opportunities(metric_rows, limit=1)
    if not priorities:
        message = "Core Web Vitals and supporting PageSpeed metrics are within target for this audit."
        st.markdown(f'<div class="recommendation-card"><h4>Result Summary</h4><p>{message}</p></div>', unsafe_allow_html=True)
        return

    top = priorities[0]
    message = (
        f"This page is mainly limited by <strong>{metric_title(top)}</strong>. "
        f"Start there before tuning lower-priority metrics."
    )
    st.markdown(
        f'<div class="recommendation-card action-card-primary"><h4>Result Summary</h4><p>{message}</p></div>',
        unsafe_allow_html=True,
    )
def render_overview(strategy, category, reference_label, metric_rows):
    primary_rows = [row for row in metric_rows if row["key"] in {"largest-contentful-paint", "cumulative-layout-shift", "INTERACTION_TO_NEXT_PAINT"}]

    st.subheader("Overview")
    cols = st.columns(3)
    for col, row in zip(cols, primary_rows):
        with col:
            render_metric_tile(row)

    st.caption(f"Benchmark set: {reference_label} · Selected category: {category} · Device: {strategy}")

    st.markdown('<div class="overview-recs">', unsafe_allow_html=True)
    st.subheader("What to Fix First")
    st.caption("Start with the metric that is furthest from a healthy user experience, then use the linked guide to investigate the page.")
    render_action_plan(metric_rows, limit=3)
    st.markdown("</div>", unsafe_allow_html=True)


def render_benchmark(metric_rows, reference_label):
    st.subheader("Metric Details")
    st.caption(f"Comparison set: {reference_label}. Open a row to see thresholds, peer median, and benchmark position.")

    st.markdown("#### Core Web Vitals")
    for row in [row for row in metric_rows if row["tier"] == "Core Web Vital"]:
        render_benchmark_card(row)

    st.markdown("#### Supporting PageSpeed Metrics")
    secondary_rows = [row for row in metric_rows if row["tier"] != "Core Web Vital"]
    for row in secondary_rows:
        label = f"{metric_title(row)} · {row['Current value']} · {row['Status']}"
        with st.expander(label, expanded=False):
            render_benchmark_card(row)

    display_df = pd.DataFrame(metric_rows).drop(
        columns=["key", "raw_value", "unit", "short", "status_class", "marker_position", "track_class", "track_style"]
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def load_component(metric_data, category, scope):
    inject_dashboard_styles()

    result = st.session_state.result
    strategy = st.session_state.strategy
    device = strategy.lower()
    pred_value = st.session_state.get("pred_value")

    lcp_reference_data, reference_label = get_reference_data(metric_data, "largest-contentful-paint", device, category, scope)
    metric_rows = build_metric_rows(result, metric_data, device, category, scope)

    tabs = st.tabs(["Overview", "Metric Details", "What-if Planner", "Raw Audit Data"])
    with tabs[0]:
        render_overview(strategy, category, reference_label, metric_rows)
    with tabs[1]:
        render_benchmark(metric_rows, reference_label)
    with tabs[2]:
        render_scenario_planner(result, device, lcp_reference_data, pred_value)
    with tabs[3]:
        render_raw_audit(result)


















