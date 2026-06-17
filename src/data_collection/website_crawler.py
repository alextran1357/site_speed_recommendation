'''
Docstring for data_collection.website_crawler

Reads the website_list.txt file to subdomains. 
Current limit it 10 pages within a given domain
'''

import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

PAGE_LIMIT = 10 
VOLUME_PATH = Path("/Volumes/workspace/site-speed-recommendation/raw_data/")
INPUT_PATH = VOLUME_PATH / "website_list_v5.txt"
OUTPUT_PATH = VOLUME_PATH / "collected_urls_v5.json"

def is_valid_url(url):
  parsed = urlparse(url)
  return bool(parsed.scheme) and bool(parsed.netloc)

def is_internal_link(base_domain, url):
  return urlparse(url).netloc == base_domain

def is_html_url(url):
  bad_extensions = (
    ".pdf", ".jpg", ".png", ".svg", ".gif",
    ".zip", ".mp4", ".mp3", ".avi", ".webm",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".json", ".xml"
  )
  return not any(url.lower().endswith(ext) for ext in bad_extensions)

def crawl_domain(start_url, max_pages=PAGE_LIMIT):
  domain = urlparse(start_url).netloc
  urls_to_visit = set([start_url])
  visited_urls = set()
  collected_urls = []
  
  while urls_to_visit and len(collected_urls) < max_pages:
    url = urls_to_visit.pop()
    
    if url in visited_urls:
      continue
    
    try:
      response = requests.get(url, timeout=7)
      if "text/html" not in response.headers.get("Content-Type", ""):
        continue
    except:
      continue
    
    visited_urls.add(url)
    collected_urls.append(url)
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    for link in soup.find_all("a", href=True):
      new_url = urljoin(url, link["href"])
      
      if is_valid_url(new_url) and is_html_url(new_url):
        if is_internal_link(domain, new_url):
          urls_to_visit.add(new_url)
          
  return collected_urls

all_results = {}

VOLUME_PATH.mkdir(parents=True, exist_ok=True)

with open(INPUT_PATH, "r") as f:
    domains = [line.strip() for line in f if line.strip()]

for d in domains:
    print(f"Crawling {d} ...")
    pages = crawl_domain(d, max_pages = 10)
    all_results[d] = pages
    print(f"Found {len(pages)} pages. \n")
  
with open(OUTPUT_PATH, "w") as f:
    json.dump(all_results, f, indent=4) 

print("Done")