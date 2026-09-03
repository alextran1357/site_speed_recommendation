'''
Docstring for util.fetch_lighthouse_data

'''
import requests
import streamlit as st

from utils.platform_guidance import detect_platform

API_KEY = st.secrets["API_KEY"]

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
        # Lighthouse typically uses 'resourceType', 'transferSize', 'requestCount'
        rtype = item.get("resourceType")
        if not rtype:
            continue
        prefix = f"resource_{rtype.lower()}"
        result[f"{prefix}_bytes"] = item.get("transferSize")
        result[f"{prefix}_requests"] = item.get("requestCount")

    return result

    """
    From 'third-party-summary', pull total transfer + requests for third-party.
    """
    tps = audits.get("third-party-summary", {}).get("details", {})
    items = tps.get("items", [])
    total_transfer = 0
    total_requests = 0

    for item in items:
        total_transfer += item.get("transferSize", 0) or 0
        total_requests += item.get("requestCount", 0) or 0

    result["third_party_transfer_bytes"] = total_transfer or None
    result["third_party_requests"] = total_requests or None
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


def extract_all_features(data):
	result = {}
	audits = data.get("audits", {}) or {}
	field_data = data.get("field_data", {}) or {}
 
	core_keys = [
		"largest-contentful-paint",
		"cumulative-layout-shift",
		"first-contentful-paint",
		"total-blocking-time",
		"speed-index",
		"interactive",  # time to interactive
	]
	extra_simple = [
		"total-byte-weight",
		"dom-size-insight",
		"unused-css-rules",
		"unused-javascript",
		"unminified-css",
		"unminified-javascript",
		"network-server-latency",
	]
	cache_type = [
		"cache-insight",
	]
	performance_score = data.get("performance_score")
	result["performance_score"] = performance_score
	result["field_data_scope"] = data.get("field_data_scope")
	result = extract_field_values(result, field_data)
	result = extract_simple_numeric_values(result, audits, core_keys)
	result = extract_simple_numeric_values(result, audits, extra_simple)
	result = extract_resource_summary(result, audits)
	result = extract_mainthread_breakdown(result, audits)
	result = extract_opportunities(result, audits)

	return result

def extract_useful_fields(data):
	result = {}

	audits = data.get("lighthouseResult", {}).get("audits", {})
	result["audits"] = audits

	categories = data.get("lighthouseResult", {}).get("categories", {})
	performance = categories.get("performance", {})
	result["performance_score"] = performance.get("score")

	url_field_data = data.get("loadingExperience", {}) or {}
	origin_field_data = data.get("originLoadingExperience", {}) or {}
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

def fetch_data(url, strategy, api_key=API_KEY):
    api_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"

    print("Calling PageSpeed API...")

    try:
        r = requests.get(
            api_url,
            params={"url": url, "strategy": strategy, "key": api_key},
            timeout=120,
        )
        data = r.json()
    except (requests.RequestException, ValueError) as error:
        print(f"ERROR: {error}")
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
