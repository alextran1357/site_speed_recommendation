"""Fetch a PageSpeed audit and extract the fields used by the dashboard."""
import os
import time

import requests
import streamlit as st

from utils.platform_guidance import detect_platform
from utils.audit_evidence import extract_audit_items, usable_audit, valid_number

def extract_simple_numeric_values(result, audits, keys):
    for k in keys:
        audit = audits.get(k, {})
        value = valid_number(audit.get("numericValue"))
        result[k] = value
    return result

def extract_field_values(result, field_data):
    page_metrics = field_data.get("metrics") if isinstance(field_data, dict) else None
    page_metrics = page_metrics if isinstance(page_metrics, dict) else {}
    field_metrics = {
        "field_largest-contentful-paint": ("LARGEST_CONTENTFUL_PAINT_MS", 1),
        "field_cumulative-layout-shift": ("CUMULATIVE_LAYOUT_SHIFT_SCORE", 0.01),
        "INTERACTION_TO_NEXT_PAINT": ("INTERACTION_TO_NEXT_PAINT", 1),
        "EXPERIMENTAL_TIME_TO_FIRST_BYTE": ("EXPERIMENTAL_TIME_TO_FIRST_BYTE", 1),
    }
    for result_key, (api_key, scale) in field_metrics.items():
        metric = page_metrics.get(api_key)
        value = valid_number(metric.get("percentile")) if isinstance(metric, dict) else None
        result[result_key] = None if value is None else value * scale
    return result

def extract_resource_summary(result, audits):
    rs = audits.get("resource-summary", {}).get("details", {})
    items = rs.get("items") if isinstance(rs.get("items"), list) else []

    for item in items:
        if not isinstance(item, dict):
            continue
        rtype = item.get("resourceType")
        if not isinstance(rtype, str) or not rtype:
            continue
        prefix = f"resource_{rtype.lower()}"
        result[f"{prefix}_bytes"] = item.get("transferSize")
        result[f"{prefix}_requests"] = item.get("requestCount")

    return result

def extract_mainthread_breakdown(result, audits):
    mt = audits.get("mainthread-work-breakdown", {}).get("details", {})
    items = mt.get("items") if isinstance(mt.get("items"), list) else []

    for item in items:
        if not isinstance(item, dict):
            continue
        group = item.get("group")
        duration = valid_number(item.get("duration"))  # ms
        if not isinstance(group, str) or not group or duration is None:
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
        overall_savings_ms = valid_number(details.get("overallSavingsMs"))
        overall_savings_bytes = valid_number(details.get("overallSavingsBytes"))

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
        if not usable_audit(audit):
            continue
        value = audit
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        result[result_key] = valid_number(value)
    return result


def extract_all_features(data):
    raw_audits = data.get("audits")
    raw_audits = raw_audits if isinstance(raw_audits, dict) else {}
    audits = {
        key: {**audit, "details": audit.get("details") if isinstance(audit.get("details"), dict) else {}}
        if usable_audit(audit) else {}
        for key, audit in raw_audits.items()
    }
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
    result["audit_items"] = extract_audit_items(raw_audits, data.get("final_url") or "")
    return result


def extract_useful_fields(data):
    lighthouse = data.get("lighthouseResult")
    lighthouse = lighthouse if isinstance(lighthouse, dict) else {}
    categories = lighthouse.get("categories")
    performance = categories.get("performance") if isinstance(categories, dict) else None
    result = {
        "audits": lighthouse.get("audits", {}),
        "final_url": lighthouse.get("finalDisplayedUrl") or lighthouse.get("finalUrl") or "",
        "performance_score": valid_number(performance.get("score")) if isinstance(performance, dict) else None,
    }
    url_field_data = data.get("loadingExperience") or {}
    origin_field_data = data.get("originLoadingExperience") or {}
    if isinstance(url_field_data, dict) and isinstance(url_field_data.get("metrics"), dict) and url_field_data["metrics"]:
        result["field_data"] = url_field_data
        result["field_data_scope"] = "URL"
    elif isinstance(origin_field_data, dict) and isinstance(origin_field_data.get("metrics"), dict) and origin_field_data["metrics"]:
        result["field_data"] = origin_field_data
        result["field_data_scope"] = "Origin"
    else:
        result["field_data"] = {}
        result["field_data_scope"] = None
    return result

def _fetch_attempt(url, strategy, api_key):
    try:
        response = requests.get(
            "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "strategy": strategy, "key": api_key},
            timeout=120,
        )
    except requests.RequestException:
        # Exceptions can contain the request URL and API key.
        print("PageSpeed request failed: connection or timeout.")
        return {"error": "The test could not finish. Please try again."}, True

    try:
        data = response.json()
    except ValueError:
        data = None
    if not response.ok:
        error = data.get("error") if isinstance(data, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        message = message if isinstance(message, str) else "No error details supplied."
        print(f"PageSpeed HTTP {response.status_code}: {message.replace(str(api_key), '[redacted]')}")
        retryable = response.status_code in (408, 429) or response.status_code >= 500
        return {"error": "The test could not finish. Please try again."}, retryable
    if not isinstance(data, dict):
        print("PageSpeed returned an unreadable response.")
        return {"error": "The test could not finish. Please try again."}, True

    cleaned = extract_useful_fields(data)
    lighthouse = data.get("lighthouseResult")
    runtime_error = lighthouse.get("runtimeError") if isinstance(lighthouse, dict) else None
    if runtime_error:
        # A failed Lighthouse run must not supply measurements or recommendations.
        cleaned["audits"] = {}
        cleaned["performance_score"] = None
    result = extract_all_features(cleaned)
    lab_available = any(result.get(key) is not None for key in (
        "largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time",
        "first-contentful-paint", "speed-index",
    ))
    if lab_available:
        result["detected_platform"] = detect_platform(cleaned.get("audits", {}), url)
        return result, False

    code = runtime_error.get("code", "UNKNOWN") if isinstance(runtime_error, dict) else "MISSING_LAB_DATA"
    print(f"Lighthouse test unavailable: {str(runtime_error or code).replace(str(api_key), '[redacted]')}")
    field_available = any(result.get(key) is not None for key in (
        "field_largest-contentful-paint", "field_cumulative-layout-shift",
        "INTERACTION_TO_NEXT_PAINT", "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
    ))
    if field_available:
        result["lab_error"] = "The simulated test could not finish. Available real-user results are shown below."
    else:
        result = {"error": "The test could not finish. Please try again."}
    retryable = code not in {
        "INVALID_URL", "NOT_HTML", "INSECURE_DOCUMENT_REQUEST", "CHROME_INTERSTITIAL_ERROR",
    }
    return result, retryable


def fetch_data(url, strategy, api_key=None):
    if api_key is None:
        api_key = os.environ.get("API_KEY") or None
    if api_key is None:
        try:
            api_key = st.secrets["API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = None
    if not api_key:
        print("PageSpeed API key is not configured.")
        return {"error": "Testing is temporarily unavailable. Please come back later."}

    partial_result = None
    for attempt in range(2):
        result, retryable = _fetch_attempt(url, strategy, api_key)
        if result.get("lab_error"):
            partial_result = result
        if not retryable:
            break
        if attempt == 0:
            print("Retrying PageSpeed once.")
            time.sleep(1)
    # Keep visitor measurements if a later attempt fails completely.
    return partial_result if result.get("error") and partial_result else result
