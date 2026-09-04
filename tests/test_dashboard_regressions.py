import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests
from streamlit.testing.v1 import AppTest

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "src" / "dashboard"
sys.path.insert(0, str(DASHBOARD_PATH))

from modules import site_tester
from utils import data_loader, fetch_lighthouse_data


class BenchmarkRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = data_loader.load_data.__wrapped__()
        cls.previous = {}
        for metric, filename in data_loader.METRIC_FILES.items():
            frame = pd.read_csv(data_loader.DATA_PATH / filename)
            frame["strategy"] = frame["strategy"].str.lower()
            if metric in data_loader.CLIP_QUANTILES:
                upper = frame[metric].quantile(data_loader.CLIP_QUANTILES[metric])
                frame[metric] = frame[metric].clip(0, upper)
            cls.previous[metric] = {
                device: frame[frame["strategy"] == device].copy()
                for device in ("mobile", "desktop")
            }

    def test_compact_tables_preserve_all_values_and_columns(self):
        for metric in self.previous:
            for device in ("mobile", "desktop"):
                with self.subTest(metric=metric, device=device):
                    pd.testing.assert_frame_equal(
                        self.current[metric][device],
                        self.previous[metric][device],
                        check_dtype=False,
                        check_categorical=False,
                    )
        memory = lambda tables: sum(
            frame.memory_usage(deep=True).sum()
            for group in tables.values()
            for frame in group.values()
        )
        self.assertLess(memory(self.current), memory(self.previous))
        self.assertTrue(data_loader.DATA_PATH.is_absolute())

    def test_categories_and_benchmark_outputs_are_unchanged(self):
        previous_categories = sorted(
            category
            for category in pd.concat(
                self.previous["largest-contentful-paint"].values(), ignore_index=True
            )["category"].dropna().unique()
            if category != "null"
        )
        self.assertEqual(site_tester.available_categories(self.current), previous_categories)
        result = {
            "largest-contentful-paint": 4800,
            "cumulative-layout-shift": 0.2,
            "total-blocking-time": 700,
            "performance_score": 0.7,
        }
        for device in ("mobile", "desktop"):
            for category, scope in (
                (None, "All sites"),
                (previous_categories[0], "Selected category"),
                ("missing-category", "Selected category"),
            ):
                with self.subTest(device=device, category=category):
                    expected = site_tester.build_metric_rows(
                        result, self.previous, device, category, scope
                    )
                    actual = site_tester.build_metric_rows(
                        result, self.current, device, category, scope
                    )
                    self.assertEqual(actual, expected)
        reference, _ = site_tester.get_reference_data(
            self.current, "largest-contentful-paint", "mobile", None, "All sites"
        )
        self.assertIs(reference, self.current["largest-contentful-paint"]["mobile"])

    def test_full_app_preserves_audit_when_platform_changes(self):
        audit = {
            "largest-contentful-paint": 4800,
            "cumulative-layout-shift": 0.3,
            "total-blocking-time": 800,
            "detected_platform": "Shopify",
            "field_data_scope": None,
        }
        with (
            patch.object(data_loader, "load_data", return_value=self.current) as load,
            patch.object(fetch_lighthouse_data, "fetch_data", return_value=audit) as fetch,
        ):
            app = AppTest.from_file(str(DASHBOARD_PATH / "app.py")).run(timeout=20)
            self.assertFalse(app.exception)
            load.assert_not_called()
            app.text_input[0].set_value("example.com")
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            fetch.assert_called_once_with("https://example.com", "mobile")
            self.assertEqual(app.session_state["website_platform"], "Shopify")
            self.assertEqual(len([item for item in app.markdown if "<style>" in item.value]), 1)
            # Start from the completed state: AppTest retains stale form widgets after st.rerun.
            completed_app = AppTest.from_file(str(DASHBOARD_PATH / "app.py"))
            for key in ("website_submitted", "result", "website", "strategy", "website_platform"):
                completed_app.session_state[key] = app.session_state[key]
            app = completed_app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual([tab.label for tab in app.tabs], ["Overview", "Detailed results"])
            self.assertEqual(
                [widget.key for widget in app.tabs[0].get("selectbox")],
                ["website_platform"],
            )
            self.assertEqual(
                [widget.key for widget in app.tabs[1].get("selectbox")],
                ["comparison_group"],
            )
            raw_sections = [
                section
                for section in app.tabs[1].get("expander")
                if section.label == "Advanced: raw audit data"
            ]
            self.assertEqual(len(raw_sections), 1)
            self.assertFalse(raw_sections[0].proto.expanded)
            self.assertEqual(len(raw_sections[0].get("dataframe")), 1)
            self.assertFalse(app.tabs[0].get("dataframe"))

            overview_cards = [
                item.proto.body
                for item in app.tabs[0].get("html")
                if "<article " in item.proto.body
            ]
            comparison = app.selectbox(key="comparison_group")
            comparison.set_value(comparison.options[1]).run(timeout=20)
            self.assertEqual(
                overview_cards,
                [
                    item.proto.body
                    for item in app.tabs[0].get("html")
                    if "<article " in item.proto.body
                ],
            )
            app.selectbox(key="website_platform").set_value("Wix").run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"], audit)
            fetch.assert_called_once()
            cards = [item.proto.body for item in app.get("html") if "<article " in item.proto.body]
            self.assertEqual(len(cards), 3)
            self.assertTrue(all("Wix" in card for card in cards))


class AuditExtractionTest(unittest.TestCase):
    def test_explicit_key_and_existing_extraction_output(self):
        response = Mock(ok=True)
        response.json.return_value = {
            "lighthouseResult": {
                "categories": {"performance": {"score": 0.7}},
                "audits": {
                    "largest-contentful-paint": {"numericValue": 4800},
                    "resource-summary": {"details": {"items": [
                        {"resourceType": "image", "transferSize": 1024, "requestCount": 2}
                    ]}},
                    "unused-javascript": {"details": {"overallSavingsBytes": 0}},
                    "network-requests": {"details": {"items": [
                        {"url": "https://cdn.shopify.com/theme.js"}
                    ]}},
                },
            },
            "originLoadingExperience": {"metrics": {
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 12}
            }},
        }
        with (
            patch.object(fetch_lighthouse_data.st, "secrets", {}),
            patch.object(fetch_lighthouse_data.requests, "get", return_value=response) as get,
        ):
            result = fetch_lighthouse_data.fetch_data("https://example.com", "mobile", api_key="test-key")
        self.assertEqual(result["largest-contentful-paint"], 4800)
        self.assertEqual(result["field_cumulative-layout-shift"], 0.12)
        self.assertEqual(result["field_data_scope"], "Origin")
        self.assertEqual(result["resource_image_bytes"], 1024)
        self.assertEqual(result["unused-javascript_savings_bytes"], 0)
        self.assertEqual(result["detected_platform"], "Shopify")
        self.assertEqual(get.call_args.kwargs["params"]["key"], "test-key")
        self.assertEqual(get.call_args.kwargs["timeout"], 120)

    def test_failed_request_does_not_log_the_api_key(self):
        output = io.StringIO()
        with (
            patch.object(
                fetch_lighthouse_data.requests, "get",
                side_effect=requests.Timeout("https://example.com?key=test-secret"),
            ),
            contextlib.redirect_stdout(output),
        ):
            result = fetch_lighthouse_data.fetch_data("https://example.com", "mobile", api_key="test-secret")
        self.assertIn("error", result)
        self.assertNotIn("test-secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
