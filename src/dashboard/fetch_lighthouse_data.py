'''
Docstring for util.fetch_lighthouse_data

Use Google PSI to grab only desktop speed data
'''
import requests
from pathlib import Path
import utils.constants as constants

API_KEY = constants.API_KEY
API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

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

def fetch_data(domain, url):
	results = {}
	print(f"\nProcessing domain: {domain}")
	results[domain] = {}
    
	print(f" Calling PageSpeed API...")
	api_request_url  = f"{API_URL}?url={url}&key={API_KEY}"
      
	try:
		r = requests.get(api_request_url, timeout=200)
		data = r.json()
	except Exception as e:
		print(f" ERROR: {e}") 
		results[domain][url] = {"error": str(e)}
		return e
		  
	cleaned = extract_useful_fields(data)
	print(f"Completed domain: {domain}")

	return cleaned