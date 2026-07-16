import pandas as pd
import streamlit as st
from pathlib import Path


DATA_PATH = Path("src/dashboard/data")

@st.cache_data
def load_data():
    lcp_data = pd.read_csv(DATA_PATH / "lcp_data.csv")

    lcp_upper = lcp_data["largest-contentful-paint"].quantile(0.999)

    lcp_data["largest-contentful-paint"] = (
        lcp_data["largest-contentful-paint"]
        .clip(0, lcp_upper)
    )

    lcp_desktop = lcp_data[lcp_data["strategy"] == "desktop"].copy()
    lcp_mobile = lcp_data[lcp_data["strategy"] == "mobile"].copy()

    return lcp_desktop, lcp_mobile