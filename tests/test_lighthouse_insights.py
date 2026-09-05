"""Lighthouse 13 schema cases based on Google's insight audit implementations."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))

from modules import site_tester
from utils import fetch_lighthouse_data


# These cases include overlapping metrics and nested per-image savings on purpose.
# https://github.com/GoogleChrome/lighthouse/tree/v13.0.0/core/audits/insights
INSIGHTS = {
    "render-blocking-insight": {
        "score": 0,
        "scoreDisplayMode": "metricSavings",
        "metricSavings": {"FCP": 900, "LCP": 350},
        "details": {"type": "table", "items": [{"wastedMs": 1200}, {"wastedMs": 800}]},
    },
    "image-delivery-insight": {
        "score": 0,
        "scoreDisplayMode": "metricSavings",
        "metricSavings": {"FCP": 50, "LCP": 100},
        "details": {
            "type": "table",
            "debugData": {"type": "debugdata", "wastedBytes": 204800},
            "items": [{
                "wastedBytes": 204800,
                "subItems": {"type": "subitems", "items": [{"wastedBytes": 204800}]},
            }],
        },
    },
    "document-latency-insight": {
        "score": 0,
        "scoreDisplayMode": "metricSavings",
        "metricSavings": {"FCP": 1800, "LCP": 1800},
        "details": {
            "type": "checklist",
            "debugData": {
                "type": "debugdata", "serverResponseTime": 950,
                "redirectDuration": 1400, "uncompressedResponseBytes": 4096,
            },
        },
    },
}
EXPECTED = {
    "render-blocking-insight": ("render-blocking-insight_lcp_savings_ms", 350, "render_blocking", "350 ms"),
    "image-delivery-insight": ("image-delivery-insight_savings_bytes", 204800, "images", "200 KB"),
    "document-latency-insight": ("document-latency-insight_server_response_ms", 950, "server", "950 ms"),
}


def insight_card_preview():
    import streamlit as st
    from modules.site_tester import build_field_metric_rows, build_priority_issues, render_recommendation_card
    from utils.fetch_lighthouse_data import extract_all_features

    result = extract_all_features({"audits": st.session_state["audit_fixture"]})
    # A real-user issue still receives supporting evidence from the current lab audit.
    result["field_largest-contentful-paint"] = 5000
    issue = build_priority_issues([], build_field_metric_rows(result))[0]
    render_recommendation_card(issue, result, "WordPress", 1)


class LighthouseInsightsTest(unittest.TestCase):
    def test_current_insights_reach_recommendation_cards(self):
        for audit_id, audit in INSIGHTS.items():
            key, value, fix_id, evidence = EXPECTED[audit_id]
            with self.subTest(audit=audit_id):
                result = fetch_lighthouse_data.extract_all_features({"audits": {audit_id: audit}})
                self.assertEqual(result[key], value)
                fix = site_tester.fix_for_issue({"issue_id": "lcp"}, result)
                self.assertEqual(fix["fix_id"], fix_id)
                self.assertIn(evidence, fix["evidence"])
                app = AppTest.from_function(insight_card_preview)
                app.session_state["audit_fixture"] = {audit_id: audit}
                app.run(timeout=20)
                self.assertFalse(app.exception)
                self.assertIn(fix["title"], app.get("html")[0].proto.body)
                self.assertIn(evidence, app.get("html")[0].proto.body)

    def test_fetch_preserves_lab_field_and_platform_with_current_insights(self):
        response = Mock(ok=True)
        response.json.return_value = {
            "lighthouseResult": {
                "categories": {"performance": {"score": 0.7}},
                "audits": {
                    **INSIGHTS,
                    "largest-contentful-paint": {"numericValue": 4800},
                    "network-requests": {"details": {"items": [
                        {"url": "https://cdn.shopify.com/theme.js"},
                    ]}},
                },
            },
            "loadingExperience": {"metrics": {
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 12},
            }},
        }
        with patch.object(fetch_lighthouse_data.requests, "get", return_value=response):
            result = fetch_lighthouse_data.fetch_data("https://example.com", "mobile", api_key="test-key")
        for key, value, _, _ in EXPECTED.values():
            self.assertEqual(result[key], value)
        self.assertEqual(result["largest-contentful-paint"], 4800)
        self.assertEqual(result["field_cumulative-layout-shift"], 0.12)
        self.assertEqual(result["field_data_scope"], "URL")
        self.assertEqual(result["detected_platform"], "Shopify")

    def test_fcp_only_savings_do_not_claim_an_lcp_improvement(self):
        for savings in ({"FCP": 900}, {"FCP": 900, "LCP": 0}):
            with self.subTest(savings=savings):
                result = fetch_lighthouse_data.extract_all_features({"audits": {
                    "render-blocking-insight": {"metricSavings": savings},
                }})
                self.assertEqual(site_tester.fix_for_issue({"issue_id": "lcp"}, result)["fix_id"], "lcp")

    def test_current_zero_or_unavailable_evidence_overrides_legacy_evidence(self):
        legacy = {
            "render-blocking-resources": {"details": {"overallSavingsMs": 999}},
            "uses-responsive-images": {"details": {"overallSavingsBytes": 999999}},
            "uses-optimized-images": {"details": {"overallSavingsBytes": 999999}},
            "network-server-latency": {"numericValue": 9999},
        }
        for current in (
            {
                "render-blocking-insight": {"metricSavings": {"LCP": 0}},
                "image-delivery-insight": {"details": {"debugData": {"wastedBytes": 0}}},
                "document-latency-insight": {"details": {"debugData": {"serverResponseTime": 0}}},
            },
            {key: {} for key in INSIGHTS},
        ):
            result = fetch_lighthouse_data.extract_all_features({"audits": {**legacy, **current}})
            self.assertEqual(site_tester.fix_for_issue({"issue_id": "lcp"}, result)["fix_id"], "lcp")

    def test_missing_failed_and_malformed_insights_are_unavailable(self):
        self.assertEqual(fetch_lighthouse_data.extract_insights({}, {}), {})
        invalid_audits = [None, {}, {"details": None}, {"metricSavings": None}]
        invalid_audits += [
            {**audit, "scoreDisplayMode": mode}
            for audit in INSIGHTS.values()
            for mode in ("error", "notApplicable", "manual")
        ]
        invalid_audits += [{**audit, "errorMessage": "Trace unavailable"} for audit in INSIGHTS.values()]
        for invalid in (float("nan"), float("inf"), -1, True, "500", None):
            invalid_audits.append({
                "metricSavings": {"LCP": invalid},
                "details": {"debugData": {"wastedBytes": invalid, "serverResponseTime": invalid}},
            })
        for audit_id, (key, _, _, _) in EXPECTED.items():
            for invalid in invalid_audits:
                with self.subTest(audit=audit_id, invalid=invalid):
                    result = fetch_lighthouse_data.extract_insights({}, {audit_id: invalid})
                    self.assertIsNone(result[key])

    def test_older_audits_still_support_recommendations(self):
        for audits, expected_fix in (
            ({"render-blocking-resources": {"details": {"overallSavingsMs": 350}}}, "render_blocking"),
            ({"uses-responsive-images": {"details": {"overallSavingsBytes": 204800}}}, "images"),
            ({"network-server-latency": {"numericValue": 950}}, "server"),
        ):
            with self.subTest(fix=expected_fix):
                result = fetch_lighthouse_data.extract_all_features({"audits": audits})
                self.assertEqual(site_tester.fix_for_issue({"issue_id": "lcp"}, result)["fix_id"], expected_fix)


if __name__ == "__main__":
    unittest.main()
