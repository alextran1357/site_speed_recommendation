from pathlib import Path

import joblib
import pandas as pd


MODEL_PATH = Path(__file__).resolve().parents[1] / "models"

FEATURE_COLUMNS = [
    "total-byte-weight",
    "dom-size-insight",
    "mainthread_other",
    "mainthread_paintCompositeRender",
    "mainthread_parseHTML",
    "mainthread_scriptEvaluation",
    "mainthread_scriptParseCompile",
    "mainthread_styleLayout",
    "network-server-latency",
    "resource_document_bytes",
    "resource_document_requests",
    "resource_font_bytes",
    "resource_font_requests",
    "resource_image_bytes",
    "resource_image_requests",
    "resource_media_bytes",
    "resource_media_requests",
    "resource_other_bytes",
    "resource_other_requests",
    "resource_script_bytes",
    "resource_script_requests",
    "resource_stylesheet_bytes",
    "resource_stylesheet_requests",
    "resource_third-party_bytes",
    "resource_third-party_requests",
    "resource_total_bytes",
    "resource_total_requests",
    "unminified-css",
    "unminified-javascript",
    "unused-css-rules",
    "unused-css-rules_savings_bytes",
    "unused-css-rules_savings_ms",
    "unused-javascript",
    "unused-javascript_savings_bytes",
    "unused-javascript_savings_ms",
    "strategy_desktop",
    "strategy_mobile",
]

def predict(features, strategy):
    model = joblib.load(MODEL_PATH / "lcp_model.joblib")
    row = pd.json_normalize(features)

    row["strategy_desktop"] = int(strategy == "desktop")
    row["strategy_mobile"] = int(strategy != "desktop")

    row = row.reindex(columns=FEATURE_COLUMNS)
    row = row.apply(pd.to_numeric, errors="coerce")

    if row.isnull().values.any():
        return None

    return model.predict(row)
