"""Fetch a PageSpeed audit and extract the fields used by the dashboard."""
import math

import requests
import streamlit as st

from utils.platform_guidance import detect_platform

def extract_simple_numeric_values(result, audits, keys):
    for k in keys:
        audit = audits.get(k, {})
        value = audit.get("numericValue")
        result[k] = value
    return result

def extract_field_values(result, field_data):
    page_metrics = field_data.get("metrics", {})
    field_metrics = {
        "field_largest-contentful-paint": ("LARGEST_CONTENTFUL_PAINT_MS", 1),
        "field_cumulative-layout-shift": ("CUMULATIVE_LAYOUT_SHIFT_SCORE", 0.01),
        "INTERACTION_TO_NEXT_PAINT": ("INTERACTION_TO_NEXT_PAINT", 1),
        "EXPERIMENTAL_TIME_TO_FIRST_BYTE": ("EXPERIMENTAL_TIME_TO_FIRST_BYTE", 1),
    }
    for result_key, (api_key, scale) in field_metrics.items():
        value = page_metrics.get(api_key, {}).get("percentile")
        result[result_key] = None if value is None else value * scale
    return result

def extract_resource_summary(result, audits):
    rs = audits.get("resource-summary", {}).get("details", {})
    items = rs.get("items", [])

    for item in items:
        rtype = item.get("resourceType")
        if not rtype:
            continue
        prefix = f"resource_{rtype.lower()}"
        result[f"{prefix}_bytes"] = item.get("transferSize")
        result[f"{prefix}_requests"] = item.get("requestCount")

    return result

def extract_mainthread_breakdown(result, audits):
    mt = audits.get("mainthread-work-breakdown", {}).get("details", {})
    items = mt.get("items", [])

    for item in items:
        group = item.get("group")
        duration = item.get("duration")  # ms
        if not group or duration is None:
            continue
        key = f"mainthread_{group}"
        result[key] = result.get(key, 0) + duration

    return result

def extract_opportunities(result, audits):
    opportunity_keys = [
        "unused-javascript",
        "unused-css-rules",
        "render-blocking-resources",
        "uses-responsive-images",
        "uses-optimized-images",
    ]
    for k in opportunity_keys:
        audit = audits.get(k, {})
        details = audit.get("details", {})
        overall_savings_ms = details.get("overallSavingsMs")
        overall_savings_bytes = details.get("overallSavingsBytes")

        if overall_savings_ms is not None:
            result[f"{k}_savings_ms"] = overall_savings_ms
        if overall_savings_bytes is not None:
            result[f"{k}_savings_bytes"] = overall_savings_bytes

    return result


def extract_insights(result, audits):
    """Read Lighthouse 13 evidence without treating time and byte savings alike."""
    # https://github.com/GoogleChrome/lighthouse/blob/v13.0.0/core/audits/insights/insight-audit.js
    fields = {
        "render-blocking-insight": (
            "render-blocking-insight_lcp_savings_ms", ("metricSavings", "LCP"),
        ),
        "image-delivery-insight": (
            "image-delivery-insight_savings_bytes", ("details", "debugData", "wastedBytes"),
        ),
        "document-latency-insight": (
            "document-latency-insight_server_response_ms",
            ("details", "debugData", "serverResponseTime"),
        ),
    }
    for audit_id, (result_key, path) in fields.items():
        if audit_id not in audits:
            continue
        # Keep unavailable new evidence explicit so old audits cannot override it.
        result[result_key] = None
        audit = audits[audit_id]
        if not isinstance(audit, dict) or audit.get("scoreDisplayMode") in {
            "error", "notApplicable", "manual",
        } or audit.get("errorMessage"):
            continue
        value = audit
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value >= 0):
            result[result_key] = value
    return result


def extract_all_features(data):
    audits = data.get("audits") or {}
    result = {
        "performance_score": data.get("performance_score"),
        "field_data_scope": data.get("field_data_scope"),
    }
    numeric_keys = [
        "largest-contentful-paint",
        "cumulative-layout-shift",
        "first-contentful-paint",
        "total-blocking-time",
        "speed-index",
        "interactive",
        "total-byte-weight",
        "dom-size-insight",
        "unused-css-rules",
        "unused-javascript",
        "unminified-css",
        "unminified-javascript",
        "network-server-latency",
    ]
    extract_field_values(result, data.get("field_data") or {})
    extract_simple_numeric_values(result, audits, numeric_keys)
    extract_resource_summary(result, audits)
    extract_mainthread_breakdown(result, audits)
    extract_opportunities(result, audits)
    extract_insights(result, audits)
    return result


def extract_useful_fields(data):
    lighthouse = data.get("lighthouseResult", {})
    result = {
        "audits": lighthouse.get("audits", {}),
        "performance_score": lighthouse.get("categories", {}).get("performance", {}).get("score"),
    }
    url_field_data = data.get("loadingExperience") or {}
    origin_field_data = data.get("originLoadingExperience") or {}
    if url_field_data.get("metrics"):
        result["field_data"] = url_field_data
        result["field_data_scope"] = "URL"
    elif origin_field_data.get("metrics"):
        result["field_data"] = origin_field_data
        result["field_data_scope"] = "Origin"
    else:
        result["field_data"] = {}
        result["field_data_scope"] = None
    return result

def fetch_data(url, strategy, api_key=None):
    if api_key is None:
        api_key = st.secrets["API_KEY"]
    api_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"

    print("Calling PageSpeed API...")

    try:
        r = requests.get(
            api_url,
            params={"url": url, "strategy": strategy, "key": api_key},
            timeout=120,
        )
        data = r.json()
    except (requests.RequestException, ValueError):
        # Request exceptions can include the URL and its API key.
        print("PageSpeed request failed.")
        return {"error": "PageSpeed Insights could not complete the request."}

    if not r.ok:
        message = data.get("error", {}).get("message", f"PageSpeed Insights returned HTTP {r.status_code}.")
        print(f"ERROR: {message}")
        return {"error": message}

    cleaned = extract_useful_fields(data)
    result = extract_all_features(cleaned)
    result["detected_platform"] = detect_platform(cleaned.get("audits", {}), url)
    print(f"Completed url: {url}")
    return result
