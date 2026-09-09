"""Collect cached PageSpeed results; shared by the desktop and mobile entry points."""
import hashlib
import json
import os
import time
from pathlib import Path

import requests


API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
VOLUME_PATH = Path("/Volumes/workspace/site-speed-recommendation/")


def extract_useful_fields(data):
    lighthouse = data.get("lighthouseResult", {})
    return {
        "audits": lighthouse.get("audits", {}),
        "performance_score": lighthouse.get("categories", {}).get("performance", {}).get("score"),
        "field_data": data.get("loadingExperience", {}),
        "origin_field_data": data.get("originLoadingExperience", {}),
    }


def run_batch(strategy="desktop", *, api_key=None, volume_path=VOLUME_PATH):
    if strategy not in {"desktop", "mobile"}:
        raise ValueError("Strategy must be desktop or mobile.")
    api_key = api_key or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("Provide a PageSpeed API key or set API_KEY.")
    volume_path = Path(volume_path)
    cache_dir = volume_path / f"{strategy}_cache"
    url_list = volume_path / "raw_data" / "collected_urls_v8.json"
    output_path = volume_path / "raw_data" / f"site_info_{strategy}_v8.json"
    with url_list.open(encoding="utf-8") as file:
        domain_url_map = json.load(file)
    cache_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for index, (domain, urls) in enumerate(domain_url_map.items(), start=1):
        print(f"Processing domain: {domain}")
        results[domain] = {}
        for url in urls:
            cache_path = cache_dir / (hashlib.md5(url.encode()).hexdigest() + ".json")
            if cache_path.exists():
                with cache_path.open(encoding="utf-8") as file:
                    data = json.load(file)
            else:
                try:
                    response = requests.get(
                        API_URL, params={"url": url, "strategy": strategy, "key": api_key}, timeout=200,
                    )
                    response.raise_for_status()
                    data = response.json()
                except (requests.RequestException, ValueError):
                    # Request exceptions can include the API key.
                    results[domain][url] = {"error": "PageSpeed Insights could not complete the request."}
                    continue
                with cache_path.open("w", encoding="utf-8") as file:
                    json.dump(data, file, indent=4)
                time.sleep(1.2)
            if not isinstance(data, dict) or data.get("error"):
                results[domain][url] = {"error": "PageSpeed Insights returned an unusable result."}
                continue
            results[domain][url] = {
                **extract_useful_fields(data), "raw_cache_path": str(cache_path),
            }
        print(f"Finished {index}/{len(domain_url_map)} domains")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, default=str)
    print(f"Saved cleaned results to {output_path}")


if __name__ == "__main__":
    key = dbutils.secrets.get(scope="site_speed_project", key="google_psi_api_key") if "dbutils" in globals() else None
    run_batch(api_key=key)
