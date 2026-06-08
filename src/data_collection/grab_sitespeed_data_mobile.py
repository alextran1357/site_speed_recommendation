'''
Docstring for data_collection.grab_sitespeed_data_mobile

Use Google PSI to grab only mobile speed data from list

All raw data is cached in the data_raw directory
'''

import json
import time
import requests
import hashlib
from pathlib import Path


API_KEY = dbutils.secrets.get(
    scope="site_speed_project",
    key="google_psi_api_key"
)
API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
STRATEGY = "mobile"

VOLUME_PATH = Path("/Volumes/workspace/site-speed-recommendation/")
CACHE_DIR = VOLUME_PATH / "mobile_cache"
URL_LIST   = VOLUME_PATH / "raw_data" / "collected_urls_v3.json"
OUT_DIR    = VOLUME_PATH / "raw_data" / "site_info_mobile_v3.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
URL_LIST.parent.mkdir(parents=True, exist_ok=True)
OUT_DIR.parent.mkdir(parents=True, exist_ok=True)

def url_to_cache_path(url):
  hashname = hashlib.md5(url.encode()).hexdigest() + ".json"
  return CACHE_DIR / hashname

def load_from_cache(url):
  path = url_to_cache_path(url)
  if path.exists():
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  return None

def save_raw_cache(url, data):
  path = url_to_cache_path(url)
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)
  return path

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

def run_batch():
  with open(URL_LIST, "r", encoding="utf-8") as f: 
    domain_url_map = json.load(f)
  
  results = {}
  
  for domain, urls in domain_url_map.items():
    print(f"\nProcessing domain: {domain}")
    results[domain] = {}
    
    for url in urls:
      print(f" -> Processing {url}")
      
      cached = load_from_cache(url)
      if cached:
        print(f" Using cached response")
        cleaned = extract_useful_fields(cached)
        cleaned["raw_cache_path"] = str(url_to_cache_path(url))
        results[domain][url] = cleaned
        continue
      
      print(f" Calling PageSpeed API...")
      api_request_url  = f"{API_URL}?url={url}&strategy={STRATEGY}&key={API_KEY}"
      
      try:
        r = requests.get(api_request_url, timeout=200)
        data = r.json()
      except Exception as e:
        print(f" ERROR: {e}") 
        results[domain][url] = {"error": str(e)}
        continue
      
      cache_path = save_raw_cache(url, data)
      
      cleaned = extract_useful_fields(data)
      cleaned["raw_cache_path"] = str(cache_path)
      results[domain][url] = cleaned
      
      print("-> Finished")
      time.sleep(1.2)
    
    print(f"Completed domain: {domain}")
  
  with open(OUT_DIR, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, default=str)
  
  print(f"\nDone! Saved cleaned results to {OUT_DIR}")
  print(f"Raw PSI responses cached in '{CACHE_DIR}/'")

if __name__ == "__main__":
    run_batch()