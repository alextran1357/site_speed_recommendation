import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path

import altair as alt
import matplotlib.pyplot as plt

from scipy.stats import percentileofscore
from utils.fetch_lighthouse_data import fetch_data
from utils.predict import predict


st.set_page_config(
    page_title="Site Speed Recommendation",
    page_icon="🚀",
    layout="wide",
)
st.title("Site Speed Recommendation")
# st.markdown("""
#     TESTING
# """)

DATA_PATH = Path("src\dashboard\data")
@st.cache_data
def load_data():
    lcp_data = pd.read_csv(DATA_PATH/"lcp_data.csv")
    lcp_upper = lcp_data['largest-contentful-paint'].quantile(0.999)
    lcp_data['largest-contentful-paint'] = lcp_data['largest-contentful-paint'].clip(0, lcp_upper)
    
    lcp_data_desktop = lcp_data[lcp_data["strategy"]=="desktop"]
    lcp_data_mobile = lcp_data[lcp_data["strategy"]=="mobile"]
    return lcp_data_desktop, lcp_data_mobile

lcp_desktop, lcp_mobile = load_data()
if "website_submitted" not in st.session_state:
    st.session_state.website_submitted = False

with st.form("website_submittion_form"):
    strategy = st.radio(
        "Select device:",
        ["Mobile", "Desktop"]
    )
    website = st.text_input(
        "Enter website to start testing",
        placeholder = "https://www.example.com",
        key = "website_submittion"
    )
    submitted = st.form_submit_button("Test PSI")
    if submitted:
        st.session_state.website_submitted = False
        with st.spinner("Testing website... This might take several minutes"):
            result = fetch_data(website, strategy)
            json_object = json.dumps(result, sort_keys=True, indent=4)
            
            if result:
                st.session_state.result = result
                st.session_state.strategy = strategy
                st.session_state.pred_value = float(predict(result, strategy.lower())[0])
                st.session_state.website_submitted = True

        st.session_state.website_submitted = True        

if st.session_state.website_submitted:
    result = st.session_state.result
    strategy = st.session_state.strategy
    pred_value = st.session_state.pred_value
    st.write(strategy)
    device = strategy.lower()
    reference_data = lcp_mobile if device == "mobile" else lcp_desktop
    
    if strategy=="Mobile":
        
        st.write(percentileofscore(reference_data['largest-contentful-paint'].values, result['largest-contentful-paint']))
        lcp_col1, lcp_col2 = st.columns(2)
        with lcp_col1:
            st.metric(
                "Current Mobile LCP",
                f"{result['largest-contentful-paint']:,.0f} ms"
            )

        with lcp_col2:
            if "estimated_new_lcp" in st.session_state:
                st.metric(
                    "Estimated LCP After Changes",
                    f"{st.session_state.estimated_new_lcp:,.0f} ms",
                    delta=f"{-st.session_state.percent_improvement:.1f}%",
                    delta_color="inverse",
                    help=(
                        "This is a model-based estimate, not a new PSI measurement. "
                        "It applies the model's predicted relative change to the site's "
                        "current PSI LCP, so the actual result may differ."
                    )
                )
            else:
                st.metric(
                    "Estimated LCP After Changes",
                    "Not tested",
                    help=(
                        "After you test optimization changes, this will show a "
                        "model-based estimate rather than an actual PSI re-test."
                    )
                )
        
        metrics = [
            ("Unused JavaScript", "unused-javascript"), 
            ("Total Byte Weight", "total-byte-weight"), 
            ("Resource Image Bytes", "resource_image_bytes"), 
            ("Resource Font Bytes", "resource_font_bytes"), 
            ("Unused CSS Rules", "unused-css-rules"), 
            ("Unused JavaScript Saving Bytes", "unused-javascript_savings_bytes")
        ]

        with st.form("optimization_form"):
            st.caption(
                "Each slider sets a metric to a percentile compared with similar "
                "sites in the selected device dataset. Lower percentiles represent "
                "smaller resource usage or fewer optimization issues and are generally better. "
                "Higher percentiles represent worse values."
            )
            reset_changes = st.form_submit_button("Reset Optimization Changes")
            if reset_changes:
                for _, metric in metrics:
                    original_percentile = int(
                        percentileofscore(
                            reference_data[metric].dropna(),
                            result[metric]
                        )
                    )
                    st.session_state[f"{device}_{metric}"] = original_percentile

                st.session_state.pop("estimated_new_lcp", None)
                st.session_state.pop("percent_improvement", None)
                st.rerun()

            col1, col2 = st.columns(2)
            selected_percentiles = {}

            for i, (label, metric) in enumerate(metrics):
                start_percentile = int(
                    percentileofscore(
                        reference_data[metric].dropna(),
                        result[metric]
                    )
                )

                column = col1 if i % 2 == 0 else col2
                with column:
                    selected_percentiles[metric] = st.slider(
                        label,
                        min_value=0,
                        max_value=100,
                        value=start_percentile,
                        key=f"{device}_{metric}",
                    )
            new_test_form_submit = st.form_submit_button("Test New Values")
            
        if new_test_form_submit:
            modified_result = result.copy()

            for metric, percentile in selected_percentiles.items():
                modified_result[metric] = np.percentile(
                    reference_data[metric].dropna(),
                    percentile
                )
            new_pred_value = float(predict(modified_result, "mobile")[0])
            percent_improvement = (
                (pred_value - new_pred_value) / pred_value
            ) * 100
            estimated_new_lcp = (
                result["largest-contentful-paint"]
                * (new_pred_value / pred_value)
            )
            st.session_state.percent_improvement = percent_improvement
            st.session_state.estimated_new_lcp = estimated_new_lcp
            st.rerun()

    else:
        result = st.session_state.result
        strategy = st.session_state.strategy
        pred_value = st.session_state.pred_value
        
        lcp_col1, lcp_col2 = st.columns(2)
        with lcp_col1:
            st.metric(
                "Current Desktop LCP",
                f"{result['largest-contentful-paint']:,.0f} ms"
            )

        with lcp_col2:
            if "estimated_new_lcp" in st.session_state:
                st.metric(
                    "Estimated LCP After Changes",
                    f"{st.session_state.estimated_new_lcp:,.0f} ms",
                    delta=f"{-st.session_state.percent_improvement:.1f}%",
                    delta_color="inverse",
                    help=(
                        "This is a model-based estimate, not a new PSI measurement. "
                        "It applies the model's predicted relative change to the site's "
                        "current PSI LCP, so the actual result may differ."
                    )
                )
            else:
                st.metric(
                    "Estimated LCP After Changes",
                    "Not tested",
                    help=(
                        "After you test optimization changes, this will show a "
                        "model-based estimate rather than an actual PSI re-test."
                    )
                )
        
        metrics = [
            ("Unused JavaScript", "unused-javascript"), 
            ("Total Byte Weight", "total-byte-weight"), 
            ("Resource Image Bytes", "resource_image_bytes"), 
            ("Resource Font Bytes", "resource_font_bytes"), 
            ("Unused CSS Rules", "unused-css-rules"), 
            ("Unused JavaScript Saving Bytes", "unused-javascript_savings_bytes")
        ]
        
        with st.form("optimization_form"):
            st.caption(
                "Each slider sets a metric to a percentile compared with similar "
                "sites in the selected device dataset. Lower percentiles represent "
                "smaller resource usage or fewer optimization issues and are generally better. "
                "Higher percentiles represent worse values."
            )
            reset_changes = st.form_submit_button("Reset Optimization Changes")
            if reset_changes:
                for _, metric in metrics:
                    original_percentile = int(
                        percentileofscore(
                            reference_data[metric].dropna(),
                            result[metric]
                        )
                    )
                    st.session_state[f"{device}_{metric}"] = original_percentile

                st.session_state.pop("estimated_new_lcp", None)
                st.session_state.pop("percent_improvement", None)
                st.rerun()

            col1, col2 = st.columns(2)
            selected_percentiles = {}

            for i, (label, metric) in enumerate(metrics):
                start_percentile = int(
                    percentileofscore(
                        reference_data[metric].dropna(),
                        result[metric]
                    )
                )

                column = col1 if i % 2 == 0 else col2
                with column:
                    selected_percentiles[metric] = st.slider(
                        label,
                        min_value=0,
                        max_value=100,
                        value=start_percentile,
                        key=f"{device}_{metric}",
                    )
            new_test_form_submit = st.form_submit_button("Test New Values")
            
        if new_test_form_submit:
            modified_result = result.copy()

            for metric, percentile in selected_percentiles.items():
                modified_result[metric] = np.percentile(
                    reference_data[metric].dropna(),
                    percentile
                )
            new_pred_value = float(predict(modified_result, "desktop")[0])
            percent_improvement = (
                (pred_value - new_pred_value) / pred_value
            ) * 100
            estimated_new_lcp = (
                result["largest-contentful-paint"]
                * (new_pred_value / pred_value)
            )
            st.session_state.percent_improvement = percent_improvement
            st.session_state.estimated_new_lcp = estimated_new_lcp
            st.rerun()