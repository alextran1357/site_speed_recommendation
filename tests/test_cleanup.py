"""Regression checks for shared collection and simplified prediction code."""
import hashlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "src/dashboard")]
from data_collection import grab_sitespeed_data_desktop as desktop
from data_collection import grab_sitespeed_data_mobile as mobile
from data_collection import feature_extractor, website_crawler
from utils import predict


class CleanupTest(unittest.TestCase):
    def test_batch_entrypoints_keep_device_paths_and_reuse_raw_cache(self):
        url = "https://example.com/shop?a=1&b=2"
        raw = {"lighthouseResult": {"categories": {"performance": {"score": 0.7}},
                                   "audits": {"largest-contentful-paint": {"numericValue": 4000}}},
               "loadingExperience": {"metrics": {}}, "originLoadingExperience": {"metrics": {"x": 1}}}
        for module, strategy in ((desktop, "desktop"), (mobile, "mobile")):
            with self.subTest(strategy=strategy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "raw_data").mkdir()
                (root / "raw_data/collected_urls_v8.json").write_text(json.dumps({"example.com": [url]}))
                response = Mock()
                response.json.return_value = raw
                with patch.object(desktop.requests, "get", return_value=response) as get, patch.object(desktop.time, "sleep"), redirect_stdout(io.StringIO()):
                    module.run_batch(api_key="test-key", volume_path=root)
                    module.run_batch(api_key="test-key", volume_path=root)
                get.assert_called_once_with(desktop.API_URL, params={"url": url, "strategy": strategy, "key": "test-key"}, timeout=200)
                cache_path = root / f"{strategy}_cache" / (hashlib.md5(url.encode()).hexdigest() + ".json")
                self.assertEqual(json.loads(cache_path.read_text()), raw)
                saved = json.loads((root / f"raw_data/site_info_{strategy}_v8.json").read_text())
                self.assertEqual(saved["example.com"][url], {**desktop.extract_useful_fields(raw), "raw_cache_path": str(cache_path)})
                row = feature_extractor.extract_all_features(saved["example.com"][url], "example.com", url, strategy)
                self.assertEqual(row["largest-contentful-paint"], 4000)
                self.assertEqual(row["strategy"], strategy)

    def test_failed_batch_request_is_not_cached_or_logged_with_credentials(self):
        for failure in (requests.Timeout("key=test-secret"), requests.HTTPError("key=test-secret")):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "raw_data").mkdir()
                (root / "raw_data/collected_urls_v8.json").write_text(json.dumps({"example.com": ["https://example.com"]}))
                output = io.StringIO()
                with patch.object(desktop.requests, "get", side_effect=failure), redirect_stdout(output):
                    desktop.run_batch(api_key="test-secret", volume_path=root)
                saved = (root / "raw_data/site_info_desktop_v8.json").read_text()
                self.assertIn('"error"', saved)
                self.assertNotIn("test-secret", saved + output.getvalue())
                self.assertEqual(list((root / "desktop_cache").iterdir()), [])

    def test_crawler_import_does_not_run_and_still_filters_internal_pages(self):
        with patch.object(website_crawler.requests, "get") as get:
            importlib.reload(website_crawler)
            get.assert_not_called()
        response = Mock(headers={"Content-Type": "text/html"}, text='<a href="/shop">Shop</a><a href="https://elsewhere.com">Other</a><a href="/image.jpg">Image</a>')
        with patch.object(website_crawler.requests, "get", return_value=response) as get:
            pages = website_crawler.crawl_domain("https://example.com", max_pages=2)
        self.assertEqual(pages, ["https://example.com", "https://example.com/shop"])
        self.assertEqual(get.call_count, 2)

    def test_prediction_preserves_feature_order_and_ignores_unneeded_fields(self):
        features = {key: 1 for key in predict.FEATURE_COLUMNS}
        features.update({"performance_score": 0.7, "largest-contentful-paint": 5000, "audit_items": {"lcp": []}})
        for strategy in ("desktop", "mobile"):
            model = Mock()
            with patch.object(predict.joblib, "load", return_value=model):
                predict.predict(features, strategy)
            row = model.predict.call_args.args[0]
            self.assertEqual(list(row.columns), predict.FEATURE_COLUMNS)
            self.assertEqual(row.loc[0, "strategy_desktop"], int(strategy == "desktop"))
            self.assertEqual(row.loc[0, "strategy_mobile"], int(strategy == "mobile"))
        with patch.object(predict.joblib, "load", return_value=model):
            model.reset_mock()
            self.assertIsNone(predict.predict({}, "mobile"))
            model.predict.assert_not_called()


if __name__ == "__main__":
    unittest.main()
