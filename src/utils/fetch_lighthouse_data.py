'''
Docstring for util.fetch_lighthouse_data

'''
import requests
from pathlib import Path
import pandas as pd

# This is used if not on databricks
# import utils.constants as constants
# API_KEY = constants.API_KEY

def extract_simple_numeric_values(result, audits, keys):
    for k in keys:
        audit = audits.get(k, {})
        value = audit.get("numericValue")
        result[k] = value
    return result

def extract_field_values(result, field_data, keys):
    page_metrics = field_data.get("metrics", {})   
    for k in keys:
        audit = page_metrics.get(k, {})
        value = audit.get("percentile")
        result[k] = value
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
	field_keys = [
		"INTERACTION_TO_NEXT_PAINT",
		"EXPERIMENTAL_TIME_TO_FIRST_BYTE",
	]
 
	performance_score = data.get("performance_score")
	result["performance_score"] = performance_score
	result = extract_field_values(result, field_data, field_keys)
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

	result["field_data"] = data.get("loadingExperience", {})
	result["origin_field_data"] = data.get("originLoadingExperience", {})

	return result

def fetch_data(api_key, url):
	API_KEY = api_key
	API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

	results = {}

	print(f"Calling PageSpeed API...")
	api_request_url  = f"{API_URL}?url={url}&key={API_KEY}"

	try:
		r = requests.get(api_request_url, timeout=200)
		data = r.json()
	except Exception as e:
		print(f" ERROR: {e}") 
		return e

	cleaned = extract_useful_fields(data)
	result = extract_all_features(cleaned)
	print(f"Completed url: {url}")
	return result

# if __name__ == "__main__":
# 	API_KEY = dbutils.secrets.get(
# 		scope="site_speed_project",
# 		key="google_psi_api_key"
# 	)
# 	fetch_data(API_KEY, "https://www.zillow.com/")