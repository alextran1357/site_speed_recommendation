'''
Docstring for data_manipulation.feature_extractor

Extract features from raw website speed jsons
'''

import json
import pandas as pd
from pathlib import Path

def extract_simple_numeric_values(audits, keys):
    """
    Extracts audits[key]['numericValue'] for each key in `keys`.
    Returns a flat dict like {'largest-contentful-paint': 1234, ...}
    """
    out = {}
    for k in keys:
        audit = audits.get(k, {})
        value = audit.get("numericValue")
        out[k] = value  # can be None if missing
    return out

def extract_field_values(field_data, keys):
    page_metrics = field_data.get("metrics", {})   
    out = {}
    for k in keys:
        audit = page_metrics.get(k, {})
        value = audit.get("percentile")
        out[k] = value  # can be None if missing
    return out

def extract_field_percentiles(field_data, keys):
    page_metrics = field_data.get("metrics", {})   
    out = {}
    for k in keys:
        audit = page_metrics.get(k,)
    return out

def extract_resource_summary(audits):
    """
    Flattens 'resource-summary' into:
    resource_script_bytes, resource_script_requests, ...
    """
    out = {}
    rs = audits.get("resource-summary", {}).get("details", {})
    items = rs.get("items", [])

    for item in items:
        # Lighthouse typically uses 'resourceType', 'transferSize', 'requestCount'
        rtype = item.get("resourceType")
        if not rtype:
            continue
        prefix = f"resource_{rtype.lower()}"
        out[f"{prefix}_bytes"] = item.get("transferSize")
        out[f"{prefix}_requests"] = item.get("requestCount")

    return out

# Lighthouse does not return an easy way to summarize third-party requests. This is no long in use.
def extract_third_party_summary(audits):
    """
    From 'third-party-summary', pull total transfer + requests for third-party.
    """
    out = {}
    tps = audits.get("third-party-summary", {}).get("details", {})
    items = tps.get("items", [])
    total_transfer = 0
    total_requests = 0

    for item in items:
        # Each item typically is per third-party domain
        total_transfer += item.get("transferSize", 0) or 0
        total_requests += item.get("requestCount", 0) or 0

    out["third_party_transfer_bytes"] = total_transfer or None
    out["third_party_requests"] = total_requests or None
    return out


def extract_mainthread_breakdown(audits):
    """
    From 'mainthread-work-breakdown', sum ms per category.
    Example categories: scriptEvaluation, scriptParseCompile, styleLayout, painting, parseHTML, garbageCollection
    """
    out = {}
    mt = audits.get("mainthread-work-breakdown", {}).get("details", {})
    items = mt.get("items", [])

    # We'll aggregate by group label
    for item in items:
        group = item.get("group")
        duration = item.get("duration")  # ms
        if not group or duration is None:
            continue
        key = f"mainthread_{group}"
        out[key] = out.get(key, 0) + duration

    return out


def extract_opportunities(audits):
    """
    Extract numeric 'overallSavingsMs' or 'overallSavingsBytes' from key opportunity audits.
    """
    opportunity_keys = [
        "unused-javascript",
        "unused-css-rules",
        "render-blocking-resources",
        "uses-responsive-images",
        "uses-optimized-images",
    ]

    out = {}
    for k in opportunity_keys:
        audit = audits.get(k, {})
        details = audit.get("details", {})
        overall_savings_ms = details.get("overallSavingsMs")
        overall_savings_bytes = details.get("overallSavingsBytes")

        if overall_savings_ms is not None:
            out[f"{k}_savings_ms"] = overall_savings_ms
        if overall_savings_bytes is not None:
            out[f"{k}_savings_bytes"] = overall_savings_bytes

    return out


def extract_all_features(page_obj, domain, url, strategy):
    """
    page_obj: dict for a single URL inside psi_results.json
    domain: parent domain
    url: this page URL
    strategy: 'desktop' or 'mobile'
    """
    # Skip error entries
    if "error" in page_obj:
        return None

    audits = page_obj.get("audits", {}) or {}
    field_data = page_obj.get("field_data", {}) or {}

    row = {
        "domain": domain,
        "url": url,
        "strategy": strategy,
        "performance_score": page_obj.get("performance_score"),
    }
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
    row.update(extract_field_values(field_data, field_keys))
    row.update(extract_simple_numeric_values(audits, core_keys))
    row.update(extract_simple_numeric_values(audits, extra_simple))
    row.update(extract_resource_summary(audits))
    # row.update(extract_third_party_summary(audits))
    row.update(extract_mainthread_breakdown(audits))
    row.update(extract_opportunities(audits))

    return row

def flatten_psi_json_to_csv(psi_json_path, output_csv_path, strategy):
    psi_json_path = Path(psi_json_path)
    output_csv_path = Path(output_csv_path)

    with psi_json_path.open("r", encoding="utf-8") as f:
        psi_data = json.load(f)

    rows = []

    for domain, urls_dict in psi_data.items():
        for url, page_obj in urls_dict.items():
            row = extract_all_features(page_obj, domain, url, strategy)
            if row is not None:
                rows.append(row)

    if not rows:
        print("No valid rows found (maybe everything errored?).")
        return

    df = pd.DataFrame(rows)

    col_order_start = [
        "domain",
        "url",
        "strategy",
        "performance_score",
        "largest-contentful-paint",
        "cumulative-layout-shift",
        "first-contentful-paint",
        "total-blocking-time",
        "speed-index",
        "interactive",
        "total-byte-weight",
    ]
    other_cols = [c for c in df.columns if c not in col_order_start]
    df = df[col_order_start + sorted(other_cols)]

    df.to_csv(output_csv_path, index=False)
    print(f"Saved {len(df)} rows → {output_csv_path}")


if __name__ == "__main__":
    VOLUME_PATH      = Path("/Volumes/workspace/site-speed-recommendation/")
    IN_DIR_MOBILE    = VOLUME_PATH / "raw_data" / "site_info_mobile_v3.json"
    IN_DIR_DESKTOP   = VOLUME_PATH / "raw_data" / "site_info_desktop_v3.json"

    OUT_DIR_MOBILE   = VOLUME_PATH / "psi_data" / "mobile_extracted_raw_v3.csv"
    OUT_DIR_DESKTOP  = VOLUME_PATH / "psi_data" / "desktop_extracted_raw_v3.csv"

    IN_DIR_MOBILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIR_MOBILE.parent.mkdir(parents=True, exist_ok=True)

    flatten_psi_json_to_csv(
        IN_DIR_DESKTOP,
        OUT_DIR_DESKTOP,
        strategy="desktop",
    )
    flatten_psi_json_to_csv(
        IN_DIR_MOBILE,
        OUT_DIR_MOBILE,
        strategy="mobile",
    )
