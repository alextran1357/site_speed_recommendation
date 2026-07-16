import pandas as pd
import streamlit as st
from pathlib import Path


DATA_PATH = Path("src/dashboard/data")

METRIC_FILES = {
    "performance_score": "performance_score_data.csv",
    "largest-contentful-paint": "lcp_data.csv",
    "cumulative-layout-shift": "cls_data.csv",
    "first-contentful-paint": "fcp_data.csv",
    "total-blocking-time": "tbt_data.csv",
    "speed-index": "speed_index_data.csv",
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "experimental_time_to_first_byte_data.csv",
    "INTERACTION_TO_NEXT_PAINT": "interaction_to_next_paint_data.csv",
    "interactive": "interactive_data.csv",
}

CLIP_QUANTILES = {
    "largest-contentful-paint": 0.999,
    "first-contentful-paint": 0.999,
    "total-blocking-time": 0.999,
    "speed-index": 0.999,
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": 0.999,
    "INTERACTION_TO_NEXT_PAINT": 0.999,
    "interactive": 0.999,
}


@st.cache_data
def load_data():
    metric_data = {}

    for metric, file_name in METRIC_FILES.items():
        data = pd.read_csv(DATA_PATH / file_name)
        data["strategy"] = data["strategy"].str.lower()

        if metric in CLIP_QUANTILES:
            upper = data[metric].quantile(CLIP_QUANTILES[metric])
            data[metric] = data[metric].clip(0, upper)

        metric_data[metric] = {
            "desktop": data[data["strategy"] == "desktop"].copy(),
            "mobile": data[data["strategy"] == "mobile"].copy(),
        }

    return metric_data
