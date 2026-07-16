import math

import numpy as np
import pandas as pd
import streamlit as st

from utils.predict import predict


METRIC_DEFINITIONS = [
    {
        "label": "Largest Contentful Paint",
        "key": "largest-contentful-paint",
        "short": "LCP",
        "unit": "ms",
        "category": "Loading speed",
        "recommendation": "Prioritize the largest above-the-fold element first: compress or resize it, preload it when appropriate, and reduce render-blocking work before it appears.",
    },
    {
        "label": "Total Page Weight",
        "key": "total-byte-weight",
        "short": "Page weight",
        "unit": "bytes",
        "category": "Overall payload",
        "recommendation": "Reduce total transferred bytes by compressing assets, removing unused files, and reviewing large scripts or media.",
    },
    {
        "label": "Image Bytes",
        "key": "resource_image_bytes",
        "short": "Images",
        "unit": "bytes",
        "category": "Images",
        "recommendation": "Compress images, resize oversized files, use modern formats, and lazy-load below-the-fold media.",
    },
    {
        "label": "Font Bytes",
        "key": "resource_font_bytes",
        "short": "Fonts",
        "unit": "bytes",
        "category": "Fonts",
        "recommendation": "Limit font families and weights, subset fonts, and preload only the font files needed for the first view.",
    },
    {
        "label": "Third-Party Bytes",
        "key": "resource_third-party_bytes",
        "short": "Third-party",
        "unit": "bytes",
        "category": "Third-party code",
        "recommendation": "Audit analytics, ads, chat widgets, tags, and embedded tools; remove or defer anything that is not business-critical.",
    },
    {
        "label": "Unused JavaScript Audit",
        "key": "unused-javascript",
        "short": "Unused JS audit",
        "unit": "score",
        "category": "JavaScript",
        "recommendation": "Split bundles, remove unused libraries, defer non-critical scripts, and review plugins or tag-manager payloads.",
    },
    {
        "label": "Unused JavaScript Savings",
        "key": "unused-javascript_savings_bytes",
        "short": "Unused JS bytes",
        "unit": "bytes",
        "category": "JavaScript",
        "recommendation": "Start with the scripts showing the largest unused-byte savings before tuning smaller resource issues.",
    },
    {
        "label": "Unused CSS Rules",
        "key": "unused-css-rules",
        "short": "Unused CSS",
        "unit": "score",
        "category": "CSS",
        "recommendation": "Remove unused styles, split route-specific CSS, and inline only critical styles needed for initial rendering.",
    },
]

SCENARIO_METRICS = [
    item for item in METRIC_DEFINITIONS if item["key"] != "largest-contentful-paint"
]


def inject_dashboard_styles():
    st.markdown(
        """
        <style>
            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stSidebar"] {
                background: #111827 !important;
            }
            .stApp,
            .stApp p,
            .stApp label,
            .stApp span,
            .stApp div,
            .stApp h1,
            .stApp h2,
            .stApp h3,
            .stApp h4,
            .stApp h5,
            .stApp h6 {
                color: #e5e7eb !important;
            }
            .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stCaptionContainer"],
            .small-muted {
                color: #cbd5e1 !important;
            }
            div[data-testid="stMetric"] {
                background: #1f2937 !important;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: none;
            }
            div[data-testid="stMetric"] * {color: #f8fafc !important;}
            div[data-testid="stMetricLabel"] p {font-size: 0.86rem; color: #cbd5e1 !important;}
            div[data-testid="stMetricValue"] {font-size: 1.55rem;}
            .insight-card,
            .benchmark-card,
            .recommendation-card {
                border: 1px solid #334155;
                border-radius: 8px;
                background: #1f2937;
                color: #e5e7eb;
                box-shadow: none;
            }
            .insight-card {padding: 16px 18px; min-height: 132px;}
            .insight-card h4,
            .benchmark-card h4,
            .recommendation-card h4 {margin: 0 0 8px 0; color: #f8fafc !important;}
            .insight-card p,
            .benchmark-card p,
            .recommendation-card p {margin: 0; color: #cbd5e1 !important; line-height: 1.5;}
            .card-emphasis {font-size: 1.35rem; font-weight: 750; color: #f8fafc !important; margin-bottom: 8px;}
            .status-good {color: #34d399 !important; font-weight: 750;}
            .status-watch {color: #fbbf24 !important; font-weight: 750;}
            .status-poor {color: #f87171 !important; font-weight: 750;}
            .benchmark-card {padding: 16px 18px; margin-bottom: 14px;}
            .benchmark-header {display: flex; justify-content: space-between; gap: 16px; align-items: baseline;}
            .benchmark-title {font-size: 1.08rem; font-weight: 750; color: #f8fafc !important;}
            .benchmark-percentile {font-size: 1.7rem; font-weight: 800; color: #f8fafc !important; text-align: right;}
            .benchmark-track {
                position: relative;
                height: 16px;
                border-radius: 999px;
                overflow: visible;
                margin: 14px 0 10px 0;
                border: 1px solid #64748b;
            }
            .peer-track {background: linear-gradient(90deg, #22c55e 0%, #22c55e 50%, #f59e0b 50%, #f59e0b 75%, #ef4444 75%, #ef4444 100%);}
            .lcp-track {background: linear-gradient(90deg, #22c55e 0%, #22c55e 42%, #f59e0b 42%, #f59e0b 67%, #ef4444 67%, #ef4444 100%);}
            .benchmark-marker {
                position: absolute;
                top: -6px;
                height: 28px;
                width: 5px;
                background: #f8fafc;
                border: 2px solid #111827;
                border-radius: 999px;
                box-shadow: 0 0 0 1px #f8fafc;
                transform: translateX(-50%);
                z-index: 2;
            }
            .scale-labels {
                display: flex;
                justify-content: space-between;
                color: #cbd5e1 !important;
                font-size: 0.78rem;
                margin-bottom: 8px;
            }
            .scale-labels span {color: #cbd5e1 !important;}
            .benchmark-meta {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px;}
            .benchmark-meta div {background: #273449; border-radius: 6px; padding: 8px 10px; color: #f8fafc !important;}
            .benchmark-meta span {display: block; color: #cbd5e1 !important; font-size: 0.78rem;}
            .recommendation-card {padding: 16px 18px; margin-bottom: 12px;}
            .recommendation-card h4 {font-size: 1.05rem;}
            .recommendation-meta {margin-bottom: 8px !important; color: #cbd5e1 !important;}
            .overview-recs {margin-top: 18px;}
            div[data-baseweb="input"] input,
            div[data-baseweb="select"] > div,
            textarea {
                background: #1f2937 !important;
                color: #f9fafb !important;
                border-color: #475569 !important;
            }
            div[role="radiogroup"] label span,
            [data-baseweb="tab"] p {
                color: #e5e7eb !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_url(url):
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def available_categories(lcp_desktop, lcp_mobile):
    data = pd.concat([lcp_desktop, lcp_mobile], ignore_index=True)
    return sorted(
        category for category in data["category"].dropna().unique() if category != "null"
    )


def get_device_data(lcp_mobile, lcp_desktop, device):
    return lcp_mobile.copy() if device == "mobile" else lcp_desktop.copy()


def get_reference_data(lcp_mobile, lcp_desktop, device, category, scope):
    reference_data = get_device_data(lcp_mobile, lcp_desktop, device)
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
    if unit == "ms":
        if value >= 1000:
            return f"{value / 1000:.2f} s"
        return f"{value:,.0f} ms"
    if unit == "bytes":
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.2f} MB"
        if value >= 1024:
            return f"{value / 1024:.0f} KB"
        return f"{value:,.0f} B"
    return f"{value:,.0f}"


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


def peer_median(reference_data, metric, unit):
    if metric not in reference_data.columns:
        return "Unavailable"
    series = pd.to_numeric(reference_data[metric], errors="coerce").dropna()
    if series.empty:
        return "Unavailable"
    return format_value(series.median(), unit)


def lcp_status(lcp_ms):
    lcp_ms = clean_number(lcp_ms)
    if lcp_ms is None:
        return "Unavailable", "small-muted"
    if lcp_ms <= 2500:
        return "Good", "status-good"
    if lcp_ms <= 4000:
        return "Needs improvement", "status-watch"
    return "Poor", "status-poor"


def peer_status(percentile):
    if percentile is None:
        return "Unavailable", "small-muted"
    if percentile < 50:
        return "Better than typical", "status-good"
    if percentile < 75:
        return "Review", "status-watch"
    return "Priority", "status-poor"


def severity_for_metric(metric_key, raw_value, percentile):
    if metric_key == "largest-contentful-paint":
        label, css_class = lcp_status(raw_value)
        return label, css_class, "Based on Core Web Vitals thresholds: good <= 2.5s, needs improvement <= 4.0s, poor > 4.0s."

    label, css_class = peer_status(percentile)
    return label, css_class, "Based on peer percentile: below 50 is strong, 50-74 needs review, 75+ is a priority."


def marker_position_for(metric_key, raw_value, percentile):
    if metric_key == "largest-contentful-paint":
        value = clean_number(raw_value)
        if value is None:
            return 0
        return int(np.clip((value / 6000) * 100, 0, 100))
    return int(np.clip(percentile or 0, 0, 100))


def build_metric_rows(result, reference_data):
    rows = []
    for metric in METRIC_DEFINITIONS:
        key = metric["key"]
        raw_value = clean_number(result.get(key))
        percentile = percentile_for(reference_data, key, raw_value)
        status, status_class, status_basis = severity_for_metric(key, raw_value, percentile)
        rows.append(
            {
                "Area": metric["category"],
                "Metric": metric["label"],
                "Current value": format_value(raw_value, metric["unit"]),
                "Peer median": peer_median(reference_data, key, metric["unit"]),
                "Percentile vs peers": None if percentile is None else round(percentile),
                "Status": status,
                "status_class": status_class,
                "Status basis": status_basis,
                "Recommendation": metric["recommendation"],
                "key": key,
                "raw_value": raw_value,
                "unit": metric["unit"],
                "short": metric["short"],
                "marker_position": marker_position_for(key, raw_value, percentile),
                "track_class": "lcp-track" if key == "largest-contentful-paint" else "peer-track",
                "track_label": "LCP thresholds" if key == "largest-contentful-paint" else "Peer percentile",
            }
        )
    return rows


def priority_score(row):
    if row["key"] == "largest-contentful-paint":
        return 0
    percentile = row["Percentile vs peers"]
    return -1 if percentile is None else percentile


def top_opportunities(metric_rows, limit=3):
    ranked = [row for row in metric_rows if row["key"] != "largest-contentful-paint"]
    ranked.sort(key=priority_score, reverse=True)
    return [row for row in ranked if priority_score(row) >= 0][:limit]


def render_insight_card(title, body, emphasis=None, emphasis_class=""):
    emphasis_html = f'<div class="card-emphasis {emphasis_class}">{emphasis}</div>' if emphasis else ""
    st.markdown(
        f"""
        <div class="insight-card">
            <h4>{title}</h4>
            {emphasis_html}
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_benchmark_card(row):
    percentile = row["Percentile vs peers"]
    percentile_label = "Unavailable" if percentile is None else f"{percentile:.0f}th peer percentile"

    if row["key"] == "largest-contentful-paint":
        headline = row["Status"]
        track_note = "Good <= 2.5s · Needs improvement <= 4.0s · Poor > 4.0s"
        explanation = f"This marker shows the measured LCP value on the Core Web Vitals scale. Peer position is secondary: {percentile_label}."
    elif percentile is None:
        headline = "Unavailable"
        track_note = "Peer percentile scale"
        explanation = "This metric was not returned by the audit."
    else:
        headline = percentile_label
        track_note = "Green < 50th · Yellow 50th-74th · Red 75th+"
        explanation = f"Worse than {percentile:.0f}% of the selected comparison set."

    st.markdown(
        f"""
        <div class="benchmark-card">
            <div class="benchmark-header">
                <div>
                    <div class="benchmark-title">{row['Metric']}</div>
                    <p>{row['Area']} · {row['track_label']}</p>
                </div>
                <div class="benchmark-percentile"><span class="{row['status_class']}">{headline}</span></div>
            </div>
            <div class="benchmark-track {row['track_class']}">
                <div class="benchmark-marker" style="left: {row['marker_position']}%;"></div>
            </div>
            <div class="scale-labels"><span>{track_note}</span><span>{row['Current value']}</span></div>
            <p><span class="{row['status_class']}">{row['Status']}</span> - {explanation}</p>
            <p class="small-muted">{row['Status basis']}</p>
            <div class="benchmark-meta">
                <div><span>This site</span>{row['Current value']}</div>
                <div><span>Peer median</span>{row['Peer median']}</div>
                <div><span>Peer position</span>{percentile_label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_benchmark_controls(lcp_mobile, lcp_desktop, device):
    categories = available_categories(lcp_desktop, lcp_mobile)
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = categories[0]
    if "comparison_scope" not in st.session_state:
        st.session_state.comparison_scope = "Selected category"

    st.subheader("Comparison Settings")
    control_col1, control_col2 = st.columns([2, 1])
    with control_col1:
        selected_category = st.selectbox(
            "Compare against category",
            categories,
            key="selected_category",
            help="Switch categories after the audit. The PSI result stays saved; only the benchmark group changes.",
        )
    with control_col2:
        comparison_scope = st.radio(
            "Benchmark group",
            ["Selected category", "All sites"],
            key="comparison_scope",
        )

    reference_key = f"{device}|{selected_category}|{comparison_scope}"
    if st.session_state.get("reference_key") != reference_key:
        st.session_state.reference_key = reference_key
        st.session_state.pop("estimated_new_lcp", None)
        st.session_state.pop("percent_improvement", None)

    return selected_category, comparison_scope


def render_recommendations(metric_rows, limit=4):
    priorities = top_opportunities(metric_rows, limit=limit)
    if not priorities:
        st.info("This audit did not return enough resource metrics to rank recommendations.")
        return

    for index, row in enumerate(priorities, start=1):
        st.markdown(
            f"""
            <div class="recommendation-card">
                <h4>{index}. {row['Area']}: {row['short']}</h4>
                <p class="recommendation-meta"><span class="{row['status_class']}">{row['Status']}</span> · {row['Current value']} now · peer median {row['Peer median']} · {row['Percentile vs peers']:.0f}th peer percentile</p>
                <p>{row['Recommendation']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_overview(result, strategy, category, reference_label, metric_rows):
    lcp_row = next((row for row in metric_rows if row["key"] == "largest-contentful-paint"), None)
    lcp_ms = clean_number(result.get("largest-contentful-paint"))
    priority_rows = top_opportunities(metric_rows)
    main_issue = priority_rows[0] if priority_rows else None

    st.subheader("Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Current {strategy} LCP", format_value(lcp_ms, "ms"))
    col2.metric("LCP Rating", lcp_row["Status"] if lcp_row else "Unavailable")
    col3.metric("Benchmark Set", reference_label)

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    with summary_col1:
        render_insight_card(
            "LCP Health",
            "This rating uses Core Web Vitals thresholds, not peer percentile. A slow page should never be green just because peers are also slow.",
            lcp_row["Status"] if lcp_row else "Unavailable",
            lcp_row["status_class"] if lcp_row else "small-muted",
        )
    with summary_col2:
        if main_issue:
            render_insight_card(
                "Top Resource Priority",
                main_issue["Recommendation"],
                main_issue["Area"],
                main_issue["status_class"],
            )
        else:
            render_insight_card("Top Resource Priority", "The audit did not return enough comparable resource data.")
    with summary_col3:
        render_insight_card(
            "Selected Category",
            "Switch categories above to reuse this same PSI audit against a different benchmark group.",
            category,
        )

    st.markdown('<div class="overview-recs">', unsafe_allow_html=True)
    st.subheader("Recommended Next Steps")
    st.caption("These are ranked by peer-relative severity for the selected comparison group.")
    render_recommendations(metric_rows, limit=4)
    st.markdown("</div>", unsafe_allow_html=True)


def render_benchmark(metric_rows, reference_label):
    st.subheader("Benchmark")
    st.caption(
        f"Comparison set: {reference_label}. LCP color uses Core Web Vitals thresholds. "
        "Supporting metric colors use peer percentile because those metrics do not have universal good/poor cutoffs."
    )

    lcp_row = next((row for row in metric_rows if row["key"] == "largest-contentful-paint"), None)
    if lcp_row:
        render_benchmark_card(lcp_row)

    st.markdown("#### Supporting Signals")
    left_col, right_col = st.columns(2)
    supporting_rows = [row for row in metric_rows if row["key"] != "largest-contentful-paint"]
    for index, row in enumerate(supporting_rows):
        with left_col if index % 2 == 0 else right_col:
            render_benchmark_card(row)

    display_df = pd.DataFrame(metric_rows).drop(
        columns=["key", "raw_value", "unit", "short", "status_class", "marker_position", "track_class", "track_label"]
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_scenario_planner(result, device, reference_data, pred_value):
    st.subheader("Scenario Planner")
    st.caption(
        "This estimates LCP if selected resource metrics looked like lower-percentile peers. "
        "It is a planning model, not a guaranteed post-fix PSI result."
    )

    col1, col2 = st.columns(2)
    col1.metric("Current measured LCP", format_value(result.get("largest-contentful-paint"), "ms"))
    if st.session_state.get("estimated_new_lcp") is not None:
        col2.metric(
            "Scenario LCP estimate",
            format_value(st.session_state.estimated_new_lcp, "ms"),
            delta=f"{st.session_state.percent_improvement:.1f}% lower",
        )
    else:
        col2.metric("Scenario LCP estimate", "Not calculated")

    if pred_value is None:
        st.warning("The model could not create a baseline prediction for this audit, so the scenario planner is unavailable.")
        return

    with st.form("optimization_form"):
        st.write("Set target peer percentiles for each resource area.")
        reset_changes = st.form_submit_button("Reset Scenario")
        if reset_changes:
            for metric in SCENARIO_METRICS:
                original_percentile = percentile_for(reference_data, metric["key"], result.get(metric["key"]))
                st.session_state[f"{device}_{metric['key']}"] = int(original_percentile or 50)
            st.session_state.pop("estimated_new_lcp", None)
            st.session_state.pop("percent_improvement", None)
            st.rerun()

        selected_percentiles = {}
        original_percentiles = {}
        col_a, col_b = st.columns(2)
        for index, metric in enumerate(SCENARIO_METRICS):
            key = metric["key"]
            start_percentile = int(round(percentile_for(reference_data, key, result.get(key)) or 50))
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
        submitted = st.form_submit_button("Estimate Scenario")

    if submitted:
        modified_result = result.copy()
        changed_metrics = 0
        for metric, percentile in selected_percentiles.items():
            if percentile == original_percentiles.get(metric):
                continue

            series = pd.to_numeric(reference_data[metric], errors="coerce").dropna()
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
    st.subheader("Audit Data")
    st.caption("Extracted PageSpeed Insights fields used by the benchmark and model.")
    rows = [{"Field": key, "Value": value} for key, value in sorted(result.items())]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def load_component(lcp_mobile, lcp_desktop):
    inject_dashboard_styles()

    result = st.session_state.result
    strategy = st.session_state.strategy
    device = strategy.lower()
    pred_value = st.session_state.get("pred_value")

    category, scope = render_benchmark_controls(lcp_mobile, lcp_desktop, device)
    reference_data, reference_label = get_reference_data(
        lcp_mobile=lcp_mobile,
        lcp_desktop=lcp_desktop,
        device=device,
        category=category,
        scope=scope,
    )
    metric_rows = build_metric_rows(result, reference_data)

    tabs = st.tabs(["Overview", "Benchmark", "Scenario Planner", "Audit Data"])
    with tabs[0]:
        render_overview(result, strategy, category, reference_label, metric_rows)
    with tabs[1]:
        render_benchmark(metric_rows, reference_label)
    with tabs[2]:
        render_scenario_planner(result, device, reference_data, pred_value)
    with tabs[3]:
        render_raw_audit(result)




