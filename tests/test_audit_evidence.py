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
    def test_script_check_uses_matching_evidence_without_cross_fallback(self):
        groups = extract_audit_items({
            "unused-javascript": table([{"url": "https://example.com/unused.js", "wastedBytes": 3000}]),
            "bootup-time": table([{"url": "https://example.com/busy.js", "total": 850}]),
        })
        for metric, value, group, filename, other in (
            ("mainthread_scriptEvaluation", 850, "script_work", "busy.js", "unused.js"),
            ("unused-javascript_savings_bytes", 3000, "unused_scripts", "unused.js", "busy.js"),
        ):
            with self.subTest(group=group):
                result = {metric: value, "audit_items": groups, "INTERACTION_TO_NEXT_PAINT": 400}
                issue = issue_for(result, "responsiveness")
                fix = site_tester.fix_for_issue(issue, result)
                finding = site_tester.owner_finding_for(issue, result, fix)
                self.assertIn(filename, finding)
                self.assertNotIn(other, finding)
                request = site_tester.help_request_for(issue, result, "WordPress", "https://example.com", "Mobile")
                self.assertIn("Starting check: " + finding, request)
                self.assertIn("not confirmed causes", request)
                result["audit_items"] = {key: items for key, items in groups.items() if key != group}
                finding = site_tester.owner_finding_for(issue, result, fix)
                self.assertIn("did not identify a matching file", finding)
                self.assertNotIn(other, finding)
        result = {"audit_items": groups}
        issue = {"issue_id": "responsiveness"}
        finding = site_tester.owner_finding_for(issue, result, site_tester.fix_for_issue(issue, result))
        self.assertNotIn(".js", finding)

    def test_processing_precedes_unused_code_and_keeps_both_in_request(self):
        groups = extract_audit_items({
            "unused-javascript": table([{"url": "https://example.com/unused.js", "wastedBytes": 1}]),
            "bootup-time": table([{"url": "https://example.com/busy.js", "total": 3000}]),
        })
        result = {"mainthread_scriptEvaluation": 3000, "unused-javascript_savings_bytes": 1,
                  "audit_items": groups, "INTERACTION_TO_NEXT_PAINT": 400}
        issue = issue_for(result, "responsiveness")
        fix = site_tester.fix_for_issue(issue, result)
        self.assertEqual(fix["evidence_group"], "script_work")
        finding = site_tester.owner_finding_for(issue, result, fix)
        self.assertIn("busy.js", finding)
        self.assertNotIn("unused.js", finding)
        message = site_tester.help_request_for(issue, result, "Shopify", "https://example.com", "Mobile")
        for detail in ("busy.js", "unused.js", "CPU", "not a measure of CPU time", "not a measurement of real-user INP"):
            self.assertIn(detail, message)
        for value in (200, 0, None, float("nan"), -1):
            result["mainthread_scriptEvaluation"] = value
            self.assertEqual(site_tester.fix_for_issue(issue, result)["evidence_group"], "unused_scripts")

    def test_lcp_wording_covers_image_text_video_and_missing_details(self):
        from utils.platform_guidance import PLATFORM_OPTIONS
        video = {"type": "node", "selector": "video.intro", "nodeLabel": "Welcome video", "snippet": '<video class="intro"></video>'}
        for node, expected in ((IMAGE, "lcp"), (TEXT, "lcp_text"), (video, "lcp"), (None, "lcp")):
            with self.subTest(node=node):
                result = {"field_largest-contentful-paint": 5000,
                          "audit_items": extract_audit_items({"lcp-breakdown-insight": lcp_audit(node)}) if node else {}}
                issue = issue_for(result)
                fix = site_tester.fix_for_issue(issue, result)
                self.assertEqual(fix["fix_id"], expected)
                if expected == "lcp":
                    self.assertEqual(fix["title"], "Check what delays the main content")
                for platform in PLATFORM_OPTIONS:
                    with patch.object(site_tester.st, "html") as render:
                        site_tester.render_recommendation_card(issue, result, platform, 1)
                    body = " ".join(call.args[0] for call in render.call_args_list)
                    self.assertNotIn("main image or text", body)
                    self.assertNotIn("image or heading", body)
                    if node is None:
                        self.assertIn("did not identify the main content", body)
                message = site_tester.help_request_for(issue, result, "Shopify", "https://example.com", "Mobile")
                if node:
                    self.assertIn(node["selector"], message)
                if expected == "lcp_text":
                    self.assertIn("font-display", message)
                else:
                    self.assertIn("server delay, resource loading, and render delay", message)

    def test_blocking_advice_uses_file_evidence_without_assuming_an_app(self):
        from utils.platform_guidance import PLATFORM_OPTIONS
        for items in ([{"url": "https://example.com/theme.css", "wastedMs": 350}], []):
            result = {"field_largest-contentful-paint": 5000, "render-blocking-insight_lcp_savings_ms": 350,
                      "audit_items": extract_audit_items({"render-blocking-insight": table(items)})}
            issue = issue_for(result)
            for platform in PLATFORM_OPTIONS:
                guidance = guidance_for(platform, "render_blocking")
                self.assertIn("help request", guidance["owner_action"])
                self.assertNotIn("popup", guidance["owner_action"])
                self.assertNotIn("animation", guidance["owner_action"])
                with patch.object(site_tester.st, "html") as render:
                    site_tester.render_recommendation_card(issue, result, platform, 1)
                body = render.call_args_list[0].args[0]
                self.assertIn("theme.css" if items else "specific blocking file", body)
                message = site_tester.help_request_for(issue, result, platform, "https://example.com", "Mobile")
                self.assertIn("script dependencies", message)
                self.assertIn("Do not assume", message)

    def test_missing_blocking_file_does_not_claim_lcp_is_missing(self):
        for node in (TEXT, IMAGE, None):
            with self.subTest(node=node):
                result = {"render-blocking-insight_lcp_savings_ms": 100,
                          "audit_items": extract_audit_items({"lcp-breakdown-insight": lcp_audit(node)}) if node else {}}
                issue = {"issue_id": "lcp"}
                finding = site_tester.owner_finding_for(issue, result, site_tester.fix_for_issue(issue, result))
                self.assertIn("specific blocking file", finding)
                self.assertNotIn("did not identify the main content", finding)

    def test_slow_initial_response_is_checked_before_downstream_savings(self):
        result = {"document-latency-insight_server_response_ms": 2000,
                  "render-blocking-insight_lcp_savings_ms": 50}
        issue = {"issue_id": "lcp"}
        fix = site_tester.fix_for_issue(issue, result)
        self.assertEqual(fix["fix_id"], "server")
        self.assertIn("Check this first", fix["evidence"])
        for latency in (0, 800, None, float("nan")):
            with self.subTest(latency=latency):
                result["document-latency-insight_server_response_ms"] = latency
                result["network-server-latency"] = 9999
                self.assertEqual(site_tester.fix_for_issue(issue, result)["fix_id"], "render_blocking")

    def test_cls_owner_copy_is_short_and_details_stay_in_help_request(self):
        from utils.platform_guidance import PLATFORM_OPTIONS
        for node in (TEXT, IMAGE, {"type": "node", "selector": "main.products", "nodeLabel": "Category Size Colors " * 30},
                     {"type": "node", "selector": "#" + "x" * 250}, None):
            with self.subTest(node=node):
                groups = extract_audit_items({"layout-shifts": table([{"node": node, "score": 0.3}])})
                result = {"audit_items": groups, "field_cumulative-layout-shift": 0.4}
                issue = issue_for(result, "cls")
                finding = site_tester.owner_finding_for(issue, result, site_tester.fix_for_issue(issue, result))
                if node in (TEXT, IMAGE):
                    self.assertIn(node["nodeLabel"], finding)
                    self.assertIn("Watch whether it moves", finding)
                elif node and node.get("nodeLabel"):
                    self.assertIn("Category Size Colors", finding)
                    self.assertIn("…", finding)
                    self.assertLess(len(finding), 210)
                elif node:
                    self.assertEqual(finding, "")
                else:
                    self.assertIn("did not identify which part moved", finding)
                for platform in PLATFORM_OPTIONS:
                    guidance = guidance_for(platform, "cls")
                    self.assertIn("what moves and when", guidance["owner_action"])
                    for clue in ("images appearing", "banners pushing", "text changing size", "scroll"):
                        self.assertIn(clue, guidance["owner_action"])
                    self.assertIn("find what causes the movement", guidance["help_action"])
                    self.assertNotIn("space available", guidance["help_action"])
                request = site_tester.help_request_for(issue, result, "WordPress", "https://example.com", "Mobile")
                if node:
                    self.assertIn(node["selector"], request)
                    self.assertIn("a moving element may not be the cause", request)

    def test_cls_unclear_labels_do_not_render_an_empty_finding(self):
        for label in ("", "div", "img", "https://example.com/a.jpg", "asset_123.jpg", "x" * 41):
            with self.subTest(label=label):
                item = {"kind": "element", "label": label, "selector": "main.products", "audit_id": "layout-shifts", "shift_score": 0.3}
                result = {"audit_items": {"layout": [item]}, "field_cumulative-layout-shift": 0.4}
                issue = issue_for(result, "cls")
                with patch.object(site_tester.st, "html") as render:
                    site_tester.render_recommendation_card(issue, result, "WordPress", 1)
                body = render.call_args_list[0].args[0]
                self.assertNotIn('class="audit-finding"', body)
                self.assertIn("what moves and when", body)
                request = site_tester.help_request_for(issue, result, "WordPress", "https://example.com", "Mobile")
                self.assertIn("main.products", request)
                self.assertIn("Starting check: Reload", request)

    def test_cls_long_label_excerpt_is_escaped_and_full_details_remain(self):
        label = 'Category Size Colors Size Type Fabric Price 759 Items Sort By Newest to Oldest & More'
        item = {"kind": "element", "label": label, "selector": "main.products", "audit_id": "layout-shifts", "shift_score": 0.3}
        result = {"audit_items": {"layout": [item]}, "field_cumulative-layout-shift": 0.4}
        issue = issue_for(result, "cls")
        with patch.object(site_tester.st, "html") as render:
            site_tester.render_recommendation_card(issue, result, "WordPress", 1)
        body = render.call_args_list[0].args[0]
        self.assertIn('area labelled “Category Size Colors Size Type Fabric Price 759…”', body)
        self.assertIn("anything appearing above it", body)
        self.assertNotIn("Newest to Oldest", body)
        self.assertIn(label, site_tester.help_request_for(issue, result, "WordPress", "https://example.com", "Mobile"))
        item["label"] = 'Delivery & "returns"'
        with patch.object(site_tester.st, "html") as render:
            site_tester.render_recommendation_card(issue, result, "WordPress", 1)
        self.assertIn('Delivery &amp; &quot;returns&quot;', render.call_args_list[0].args[0])
        self.assertEqual(site_tester.issue_title_for(issue), "Content moves unexpectedly")
        self.assertEqual(site_tester.issue_title_for({**issue, "source": "Lab"}), "Content moves while the page loads")

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
