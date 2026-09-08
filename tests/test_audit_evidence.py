"""Item evidence uses Lighthouse's list/table/node shapes, including partial reports."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/dashboard"))
from modules import site_tester
from utils.audit_evidence import extract_audit_items
from utils.fetch_lighthouse_data import extract_all_features
from utils.platform_guidance import guidance_for


IMAGE = {"type": "node", "selector": "main > img.hero", "nodeLabel": "Summer collection", "snippet": '<img src="https://example.com/hero.jpg" alt="Summer collection">'}
TEXT = {"type": "node", "selector": "main > h1", "nodeLabel": "Welcome to our store", "snippet": '<h1 class="title">Welcome to our store</h1>'}


def table(items):
    return {"details": {"type": "table", "items": items}}


def lcp_audit(node):
    return {"details": {"type": "list", "items": [
        {"type": "table", "items": [{"subpart": "elementRenderDelay", "duration": 1200}]}, node,
    ]}}


def issue_for(result, issue_id="lcp"):
    rows = site_tester.build_field_metric_rows(result)
    return next(item for item in site_tester.build_priority_issues([], rows, result.get("field_data_scope")) if item["issue_id"] == issue_id)


class AuditEvidenceTest(unittest.TestCase):
    def test_all_finding_types_keep_units_and_skip_totals_and_subitems(self):
        audits = {
            "lcp-breakdown-insight": lcp_audit(IMAGE),
            "image-delivery-insight": table([
                {"url": "https://example.com/other.jpg", "wastedBytes": 9000},
                {"node": IMAGE, "url": "https://example.com/hero.jpg", "wastedBytes": 2000,
                 "subItems": {"type": "subitems", "items": [{"wastedBytes": 2000}]}},
            ]),
            "render-blocking-insight": table([{"url": "https://example.com/site.css", "wastedMs": 700}]),
            "unused-javascript": table([{"url": "https://example.com/chat.js", "wastedBytes": 3000}]),
            "bootup-time": table([{"url": "https://example.com/shop.js", "total": 850}]),
            "cls-culprits-insight": {"details": {"type": "list", "items": [table([
                {"node": {"type": "text", "value": "Total"}, "score": 0.9},
                {"node": TEXT, "score": 0.2, "subItems": {"items": [{"extra": IMAGE}]}},
            ])["details"]]}},
        }
        items = extract_audit_items(audits)
        self.assertEqual(items["lcp"][0]["kind"], "image")
        self.assertEqual(len(items["images"]), 2)
        self.assertEqual(items["images"][0]["url"], "https://example.com/hero.jpg")
        self.assertEqual(items["images"][0]["savings_bytes"], 2000)
        self.assertEqual(items["render_blocking"][0]["duration_ms"], 700)
        self.assertEqual(items["unused_scripts"][0]["savings_bytes"], 3000)
        self.assertEqual(items["script_work"][0]["cpu_ms"], 850)
        self.assertEqual(len(items["layout"]), 1)
        self.assertEqual(items["layout"][0]["shift_score"], 0.2)

    def test_text_lcp_does_not_receive_unrelated_image_fix(self):
        result = extract_all_features({"audits": {
            "lcp-breakdown-insight": lcp_audit(TEXT),
            "image-delivery-insight": {**table([{"url": "https://example.com/other.jpg", "wastedBytes": 500000}]),
                                       "metricSavings": {"LCP": 100}},
        }})
        result["image-delivery-insight_savings_bytes"] = 500000
        result["field_largest-contentful-paint"] = 5000
        issue = issue_for(result)
        fix = site_tester.fix_for_issue(issue, result)
        self.assertEqual(fix["fix_id"], "lcp_text")
        self.assertIn("text", guidance_for("Shopify", fix["fix_id"])["owner_action"])
        self.assertIn("Shopify", guidance_for("Shopify", fix["fix_id"])["help_action"])
        self.assertIn('Text: "Welcome to our store"', site_tester.owner_finding_for(issue, result, fix))
        request = site_tester.help_request_for(issue, result, "Shopify", "https://example.com", "Mobile")
        self.assertIn("font-display", request)
        self.assertIn("main > h1", request)
        self.assertIn("not element attribution from real-user data", request)
        self.assertIn("Image savings do not establish an LCP cause", request)

    def test_matching_lcp_image_is_kept_even_below_the_top_three_savings(self):
        images = [{"url": f"https://example.com/{index}.jpg", "wastedBytes": 9999} for index in range(8)]
        images.append({"node": IMAGE, "url": "https://example.com/hero.jpg", "wastedBytes": 1000})
        result = extract_all_features({"audits": {"lcp-breakdown-insight": lcp_audit(IMAGE), "image-delivery-insight": table(images)}})
        issue = {"issue_id": "lcp"}
        fix = site_tester.fix_for_issue(issue, result)
        self.assertEqual(fix["fix_id"], "images")
        self.assertEqual(len(result["audit_items"]["images"]), 3)
        self.assertIn("1,000 B", fix["evidence"])

    def test_relative_urls_use_final_page_and_zero_totals_do_not_claim_savings(self):
        image = {**IMAGE, "snippet": '<img src="/hero.jpg">'}
        result = extract_all_features({"final_url": "https://example.com/redirected/page", "audits": {
            "lcp-breakdown-insight": lcp_audit(image),
            "image-delivery-insight": {"details": {"type": "table", "debugData": {"wastedBytes": 0},
                "items": [{"url": "/hero.jpg", "wastedBytes": 1000}]}},
        }})
        self.assertEqual(result["audit_items"]["lcp"][0]["url"], "https://example.com/hero.jpg")
        self.assertEqual(site_tester.fix_for_issue({"issue_id": "lcp"}, result)["fix_id"], "lcp")

    def test_partial_metadata_and_non_object_api_response_do_not_crash(self):
        from unittest.mock import Mock
        from utils import fetch_lighthouse_data
        result = fetch_lighthouse_data.extract_useful_fields({"lighthouseResult": {"categories": None}, "loadingExperience": {"metrics": []}})
        self.assertIsNone(result["performance_score"])
        self.assertIsNone(result["field_data_scope"])
        for ok, data in ((True, []), (False, []), (False, {"error": None})):
            response = Mock(ok=ok, status_code=500)
            response.json.return_value = data
            with patch.object(fetch_lighthouse_data.requests, "get", return_value=response):
                result = fetch_lighthouse_data.fetch_data("https://example.com", "mobile", api_key="test-key")
            self.assertIn("error", result)

    def test_missing_element_and_failed_measurement_are_distinct(self):
        self.assertEqual(site_tester.fix_for_issue({"issue_id": "lcp"}, {"image-delivery-insight_savings_bytes": 500000})["fix_id"], "lcp")
        for audit in ({"numericValue": 5000}, {"numericValue": 5000, "scoreDisplayMode": "error"}):
            result = extract_all_features({"audits": {"largest-contentful-paint": audit}})
            expected = None if "scoreDisplayMode" in audit else 5000
            self.assertEqual(result["largest-contentful-paint"], expected)
            self.assertEqual(result["audit_items"]["lcp"], [])
        result["field_largest-contentful-paint"] = 5000
        issue = issue_for(result)
        self.assertIn("did not identify", site_tester.owner_finding_for(issue, result, site_tester.fix_for_issue(issue, result)))
        self.assertIn("not identified", site_tester.help_request_for(issue, result, "Other / Not sure", "https://example.com", "Desktop"))

    def test_current_unavailable_details_do_not_revive_legacy_findings(self):
        legacy = table([{"node": IMAGE, "url": "https://example.com/hero.jpg", "wastedBytes": 3000}])
        for invalid in (None, {}, {"scoreDisplayMode": "error", **legacy}, {"notApplicable": True, **legacy}, {"errorMessage": "failed", **legacy}):
            items = extract_audit_items({"image-delivery-insight": invalid, "uses-responsive-images": legacy})
            self.assertEqual(items["images"], [])
        items = extract_audit_items({"uses-responsive-images": legacy, "uses-optimized-images": legacy,
                                     "largest-contentful-paint-element": table([{"node": IMAGE}])})
        self.assertEqual(len(items["images"]), 1)
        self.assertEqual(items["lcp"][0]["kind"], "image")

    def test_malformed_values_nodes_and_unsafe_urls_are_ignored(self):
        rows = [None, "bad", {"node": {"type": "text", "value": "Total"}, "score": 0.5}]
        for value in (None, True, -1, float("nan"), float("inf"), "900"):
            rows.append({"url": "https://example.com/app.js", "wastedBytes": value})
        for url in ("javascript:alert(1)", "data:text/plain,secret", "https://user:pass@example.com/a", "http://[", 12):
            rows.append({"url": url, "wastedBytes": 1000})
        items = extract_audit_items({"unused-javascript": table(rows), "lcp-breakdown-insight": {"details": {"items": None}}})
        self.assertEqual(items["unused_scripts"], [])
        self.assertEqual(items["lcp"], [])
        for audit in (None, [], {"details": None}, {"details": {"items": [None, 1, {}]}}):
            result = extract_all_features({"audits": {key: audit for key in ("largest-contentful-paint", "resource-summary", "mainthread-work-breakdown", "unused-javascript", "image-delivery-insight")}})
            self.assertIsNone(result["largest-contentful-paint"])

    def test_conflicting_nodes_stay_unknown_and_background_discovery_is_image(self):
        items = extract_audit_items({"lcp-breakdown-insight": lcp_audit(TEXT), "lcp-discovery-insight": lcp_audit(IMAGE)})
        self.assertEqual(items["lcp"], [])
        background = {"type": "node", "selector": "div.hero", "snippet": '<div class="hero">'}
        items = extract_audit_items({"lcp-breakdown-insight": lcp_audit(background), "lcp-discovery-insight": lcp_audit(background)})
        self.assertEqual(items["lcp"][0]["kind"], "image")

    def test_item_labels_are_escaped_in_cards_but_present_in_help_text(self):
        node = {**TEXT, "nodeLabel": '<script>alert("x")</script>'}
        result = extract_all_features({"audits": {"lcp-breakdown-insight": lcp_audit(node)}})
        result["field_largest-contentful-paint"] = 5000
        with patch.object(site_tester.st, "html") as renderer:
            site_tester.render_recommendation_card(issue_for(result), result, "WordPress", 1)
        rendered = "".join(call.args[0] for call in renderer.call_args_list)
        self.assertNotIn('<script>alert', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_full_app_allows_partial_report_when_lcp_is_missing(self):
        from utils import fetch_lighthouse_data
        result = extract_all_features({"audits": {"cumulative-layout-shift": {"numericValue": 0.3}}})
        with patch.object(fetch_lighthouse_data, "fetch_data", return_value=result):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/dashboard/app.py")).run(timeout=20)
            app.text_input[0].set_value("example.com")
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["website_submitted"])
            self.assertTrue(any("Loading speed could not be measured" in item.value for item in app.warning))
            self.assertTrue(any("Content moves" in item.proto.body for item in app.get("html")))


def evidence_preview():
    import streamlit as st
    from utils.data_loader import load_data

    st.set_page_config(layout="centered")
    st.caption("Item evidence preview — sample data, not a live audit")
    scenario = st.selectbox("Sample finding", ["Text LCP", "Image LCP", "Missing LCP"])
    audits = {
        "largest-contentful-paint": {"numericValue": 6000},
        "cumulative-layout-shift": {"numericValue": 0.3},
        "total-blocking-time": {"numericValue": 800},
        "image-delivery-insight": table([{"node": IMAGE, "url": "https://example.com/hero.jpg", "wastedBytes": 420000}]),
        "unused-javascript": table([{"url": "https://example.com/chat.js", "wastedBytes": 250000}]),
        "bootup-time": table([{"url": "https://example.com/shop.js", "total": 850}]),
        "cls-culprits-insight": table([{"node": TEXT, "score": 0.3}]),
    }
    if scenario == "Missing LCP":
        audits["largest-contentful-paint"] = {"scoreDisplayMode": "error"}
    else:
        audits["lcp-breakdown-insight"] = lcp_audit(TEXT if scenario == "Text LCP" else IMAGE)
    result = extract_all_features({"audits": audits})
    result.update({"field_largest-contentful-paint": 9000, "field_cumulative-layout-shift": 0.3,
                   "INTERACTION_TO_NEXT_PAINT": 350, "field_data_scope": "URL", "detected_platform": "WordPress"})
    st.session_state.result = result
    st.session_state.website = "https://example.com/preview"
    st.session_state.strategy = "Mobile"
    site_tester.inject_dashboard_styles()
    site_tester.load_component(load_data())


if __name__ == "__main__":
    if "--preview" in sys.argv:
        evidence_preview()
    else:
        unittest.main()
