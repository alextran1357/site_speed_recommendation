import streamlit as st

from modules.site_tester import load_component, normalize_url
from utils.data_loader import load_data
from utils.fetch_lighthouse_data import fetch_data
from utils.predict import predict

st.set_page_config(
    page_title="Site Speed Insight",
    page_icon="🚀",
    layout="wide",
)

lcp_desktop, lcp_mobile = load_data()
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
        .stCaption,
        [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p {
            color: #cbd5e1 !important;
        }
        div[data-baseweb="input"] input,
        div[data-baseweb="select"] > div,
        textarea {
            background: #1f2937 !important;
            color: #f9fafb !important;
            border-color: #475569 !important;
        }
        div[role="radiogroup"] label span {
            color: #e5e7eb !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "website_submitted" not in st.session_state:
    st.session_state.website_submitted = False

st.title("Site Speed Insight")
st.caption(
    "Run a PageSpeed Insights audit, then compare the result against different site categories without rerunning the test."
)

with st.form("website_submission_form"):
    st.warning(
        "This runs a PageSpeed Insights audit. Lab results can vary between runs and may differ from field Core Web Vitals.",
        icon="⚠️",
    )
    strategy = st.radio("Select device:", ["Mobile", "Desktop"])
    website = st.text_input(
        "Enter website to start testing",
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
        elif result.get("largest-contentful-paint") is None:
            st.error("The audit completed, but LCP was unavailable for this URL.")
        else:
            prediction = predict(result, strategy.lower())
            st.session_state.result = result
            st.session_state.website = normalized_website
            st.session_state.strategy = strategy
            st.session_state.pred_value = None if prediction is None else float(prediction[0])
            st.session_state.website_submitted = True

if st.session_state.website_submitted:
    st.divider()
    st.caption(f"Audit: {st.session_state.website} · {st.session_state.strategy}")
    load_component(lcp_mobile=lcp_mobile, lcp_desktop=lcp_desktop)
else:
    st.info("Run a PSI audit to view the dashboard.")


