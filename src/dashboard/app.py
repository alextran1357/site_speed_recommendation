import streamlit as st

from modules.site_tester import inject_dashboard_styles, load_component, normalize_url, render_benchmark_controls
from utils.data_loader import load_data
from utils.fetch_lighthouse_data import fetch_data
from utils.platform_guidance import PLATFORM_OPTIONS

st.set_page_config(
    page_title="Site Speed Insight",
    page_icon="🚀",
    layout="centered",
)

inject_dashboard_styles()

if "website_submitted" not in st.session_state:
    st.session_state.website_submitted = False

st.title("Site Speed Insight")
st.caption(
    "Run a PageSpeed Insights audit, then compare the result against different site categories without rerunning the test."
)

submitted = False
if st.session_state.website_submitted:
    audit_col, action_col = st.columns([4, 1])
    with audit_col:
        st.success(
            f"Audit complete: {st.session_state.website} · {st.session_state.strategy}",
            icon="✅",
        )
    with action_col:
        if st.button("Run another audit", width="stretch"):
            st.session_state.website_submitted = False
            st.rerun()
else:
    with st.form("website_submission_form"):
        st.warning(
            "This runs a PageSpeed Insights audit. Lab results can vary between runs and may differ from field Core Web Vitals.",
            icon="⚠️",
        )
        strategy = st.radio("Select device:", ["Mobile", "Desktop"])
        website = st.text_input(
            "Enter website to start testing",
            value=st.session_state.get("last_website_input", ""),
            placeholder="https://www.example.com",
            key="website_submission",
        )
        submitted = st.form_submit_button("Run PSI Audit", type="primary")


if submitted:
    normalized_website = normalize_url(website)
    if not normalized_website:
        st.error("Enter a website URL before running the audit.")
    else:
        st.session_state.website_submitted = False
        st.session_state.pop("estimated_new_lcp", None)
        st.session_state.pop("percent_improvement", None)

        with st.spinner("Running PageSpeed Insights audit..."):
            result = fetch_data(normalized_website, strategy.lower())

        if not isinstance(result, dict) or not result:
            st.error("The PageSpeed audit did not return usable data. Check the URL and try again.")
        elif result.get("error"):
            st.error(f"The PageSpeed audit failed: {result['error']}")
        elif result.get("largest-contentful-paint") is None:
            st.error("The audit completed, but LCP was unavailable for this URL.")
        else:
            st.session_state.result = result
            st.session_state.website = normalized_website
            st.session_state.last_website_input = normalized_website
            st.session_state.strategy = strategy
            detected_platform = result.get("detected_platform")
            st.session_state.website_platform = (
                detected_platform if detected_platform in PLATFORM_OPTIONS else "Other / Not sure"
            )
            st.session_state.website_submitted = True
            st.rerun()

if st.session_state.website_submitted:
    metric_data = load_data()
    comparison_device = st.session_state.strategy.lower()
    category, comparison_scope = render_benchmark_controls(metric_data, comparison_device)
    load_component(metric_data=metric_data, category=category, scope=comparison_scope)
else:
    st.info("Run a PSI audit to view the dashboard.")





