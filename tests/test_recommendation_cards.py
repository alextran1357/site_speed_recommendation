import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))

from modules import site_tester
from utils.platform_guidance import PLATFORM_HELP, PLATFORM_OPTIONS, PLATFORM_SUPPORT
from utils.data_loader import load_data


def recommendation_preview():
    import streamlit as st
    from modules.site_tester import (
        inject_dashboard_styles,
        load_component,
    )
    from utils.data_loader import load_data

    st.set_page_config(layout="centered")
    st.caption("Recommendation preview — sample data, not a live audit")
    inject_dashboard_styles()
    source = st.selectbox("Measurement source", ["Field", "Lab"])
    result = {
        "field_largest-contentful-paint": 9000,
        "field_cumulative-layout-shift": 0.3,
        "INTERACTION_TO_NEXT_PAINT": 350,
    } if source == "Field" else {
        "largest-contentful-paint": 7960,
        "cumulative-layout-shift": 0.102,
        "total-blocking-time": 4600,
        "unused-javascript_savings_bytes": 1394606,
    }
    result["detected_platform"] = "WordPress"
    result["field_data_scope"] = "URL" if source == "Field" else None
    st.session_state.result = result
    st.session_state.strategy = "Mobile"
    load_component(load_data())


def audit_rows(result):
    rows = site_tester.build_metric_rows(result, load_data(), "mobile", None, "All sites")
    lab = [row for row in rows if row["short"] in {"LCP", "CLS", "TBT"}]
    return lab, site_tester.build_field_metric_rows(result)

class RecommendationCardsTest(unittest.TestCase):
    def test_summary_explains_the_screenshot_results_in_plain_language(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 22410, "cumulative-layout-shift": 0.062,
            "total-blocking-time": 1100, "field_largest-contentful-paint": 2760,
            "field_cumulative-layout-shift": 0.160, "INTERACTION_TO_NEXT_PAINT": 191,
        })
        summary = site_tester.results_interpretation(lab, field, "URL")
        self.assertEqual(summary["title"], "Focus on loading speed and moving content")
        self.assertIn("main content takes too long to appear", summary["body"])
        self.assertIn("content moves more than it should", summary["body"])
        self.assertIn("Clicks and taps respond within the recommended time", summary["body"])
        self.assertIn("Start with the fixes below", summary["body"])
        self.assertNotIn("above-target", summary["body"].lower())

    def test_complete_page_field_results_can_be_healthy_despite_lab_problems(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 5000, "cumulative-layout-shift": 0.3, "total-blocking-time": 800,
            "field_largest-contentful-paint": 2000, "field_cumulative-layout-shift": 0.05,
            "INTERACTION_TO_NEXT_PAINT": 150,
        })
        interpretation = site_tester.results_interpretation(lab, field, "URL")
        self.assertEqual(interpretation["tone"], "mixed")
        self.assertIn("The available visitor results look good", interpretation["title"])
        self.assertIn("Use the checks below", interpretation["body"])
        self.assertNotIn("unavailable", interpretation["body"])

    def test_interpretation_does_not_treat_missing_field_data_as_healthy(self):
        lab, field = audit_rows({"largest-contentful-paint": 5000})
        interpretation = site_tester.results_interpretation(lab, field)
        self.assertEqual(interpretation["tone"], "caution")
        self.assertEqual(interpretation["title"], "We only have a simulated test")
        self.assertIn("not enough real-user data", interpretation["body"])
        self.assertIn("The simulated test has no result for: moving content, response during loading", interpretation["body"])

    def test_partial_field_results_name_known_and_missing_areas(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 5000, "cumulative-layout-shift": 0.05, "total-blocking-time": 800,
            "field_cumulative-layout-shift": 0.05,
        })
        interpretation = site_tester.results_interpretation(lab, field, "URL")
        self.assertEqual(interpretation["tone"], "caution")
        self.assertEqual(interpretation["title"], "Some visitor results are missing")
        self.assertIn("Content stays reasonably steady", interpretation["body"])
        self.assertIn("We do not have visitor results for: loading speed, click and tap response", interpretation["body"])
        self.assertNotIn("look better", interpretation["title"])

    def test_partial_failing_field_data_still_prioritizes_known_page_problem(self):
        lab, field = audit_rows({
            "cumulative-layout-shift": 0.3,
            "field_largest-contentful-paint": 3200,
        })
        interpretation = site_tester.results_interpretation(lab, field, "URL")
        issues = site_tester.build_priority_issues(lab, field, "URL")
        self.assertEqual(interpretation["tone"], "poor")
        self.assertIn("Start with the fixes below for these visitor problems", interpretation["body"])
        self.assertIn("We do not have visitor results for: moving content, click and tap response", interpretation["body"])
        self.assertEqual((issues[0]["issue_id"], issues[0]["source"]), ("lcp", "Field"))

    def test_origin_results_do_not_claim_this_page_is_healthy_or_failing(self):
        for lcp, expected_tone in ((2000, "caution"), (5000, "poor")):
            with self.subTest(lcp=lcp):
                lab, field = audit_rows({
                    "largest-contentful-paint": 5000, "cumulative-layout-shift": 0.05,
                    "total-blocking-time": 0, "field_largest-contentful-paint": lcp,
                    "field_cumulative-layout-shift": 0.05, "INTERACTION_TO_NEXT_PAINT": 150,
                })
                interpretation = site_tester.results_interpretation(lab, field, "Origin")
                self.assertEqual(interpretation["tone"], expected_tone)
                self.assertIn("across this website", interpretation["body"])
                self.assertNotIn("Start with these page-level", interpretation["body"])
                self.assertIn("confirm", interpretation["body"].lower())
                self.assertIn("Use the checks below", interpretation["body"])

    def test_unavailable_measurements_and_unknown_scope_stay_explicit(self):
        lab, field = audit_rows({})
        interpretation = site_tester.results_interpretation(lab, field)
        self.assertEqual(interpretation["tone"], "caution")
        self.assertNotIn("healthy", str(interpretation))
        self.assertIn("not enough data", interpretation["title"])
        lab, field = audit_rows({"field_largest-contentful-paint": 2000})
        interpretation = site_tester.results_interpretation(lab, field)
        self.assertIn("whether these visitor results cover this page or the whole website", interpretation["body"])
        self.assertIn("The simulated test has no result", interpretation["body"])

    def test_page_field_issues_precede_more_severe_lab_issues(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 9000, "cumulative-layout-shift": 0.3,
            "total-blocking-time": 0, "field_largest-contentful-paint": 3200,
        })
        issues = site_tester.build_priority_issues(lab, field, "URL")
        self.assertEqual(
            [(issue["issue_id"], issue["source"], issue["Status"]) for issue in issues],
            [("lcp", "Field", "Needs improvement"), ("cls", "Lab", "Poor")],
        )
        self.assertIn("page-level visitor problems take priority", site_tester.priority_reason_for(issues[0]))

    def test_origin_and_unknown_scope_use_severity_including_same_metric(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 9000, "cumulative-layout-shift": 0.3,
            "field_largest-contentful-paint": 3200,
        })
        for scope in ("Origin", None):
            with self.subTest(scope=scope):
                issues = site_tester.build_priority_issues(lab, field, scope)
                self.assertEqual([(issue["issue_id"], issue["source"]) for issue in issues],
                                 [("lcp", "Lab"), ("cls", "Lab")])

    def test_severity_then_relative_distance_order_page_field_issues(self):
        lab, field = audit_rows({
            "field_largest-contentful-paint": 9000, "field_cumulative-layout-shift": 0.3,
            "INTERACTION_TO_NEXT_PAINT": 350,
        })
        issues = site_tester.build_priority_issues(lab, field, "URL")
        self.assertEqual([issue["issue_id"] for issue in issues], ["lcp", "cls", "responsiveness"])

    def test_origin_evidence_breaks_severity_ties_and_is_labeled_on_all_cards(self):
        lab, field = audit_rows({
            "largest-contentful-paint": 9000, "field_largest-contentful-paint": 5000,
        })
        issue = site_tester.build_priority_issues(lab, field, "Origin")[0]
        self.assertEqual(issue["source"], "Field")
        for rank in (1, 2):
            with self.subTest(rank=rank), patch.object(site_tester.st, "html") as renderer:
                site_tester.render_recommendation_card(issue, {}, "WordPress", rank)
                card = renderer.call_args.args[0]
                self.assertIn("Website-wide real-user data", card)
                if rank == 1:
                    self.assertIn("website-wide finding needs checking on this page", card)
                else:
                    self.assertNotIn("First by severity", card)

    def test_overview_passes_scope_to_summary_and_first_card(self):
        result = {
            "largest-contentful-paint": 2000, "cumulative-layout-shift": 0.3,
            "total-blocking-time": 0, "field_largest-contentful-paint": 3200,
            "field_cumulative-layout-shift": 0.05, "INTERACTION_TO_NEXT_PAINT": 150,
        }
        for scope, expected_title, first_title in (
            ("URL", "Focus on loading speed", "Largest Contentful Paint"),
            ("Origin", "Focus on loading speed", "Cumulative Layout Shift"),
        ):
            with self.subTest(scope=scope):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/dashboard/app.py"))
                app.session_state["website_submitted"] = True
                app.session_state["website"] = "https://example.com"
                app.session_state["strategy"] = "Mobile"
                app.session_state["result"] = {**result, "field_data_scope": scope}
                app.run(timeout=20)
                self.assertFalse(app.exception)
                bodies = [item.proto.body for item in app.tabs[0].get("html")]
                summary = next(body for body in bodies if "meaning-card" in body)
                cards = [body for body in bodies if "<article " in body]
                self.assertIn(expected_title, summary)
                self.assertIn(first_title, cards[0])
                self.assertIn("First ", cards[0])
                self.assertEqual(len(cards), 2)

    def test_overview_targets_stay_concise(self):
        row = {"lower_is_better": True, "good_threshold": 200, "unit": "ms"}

        self.assertEqual(site_tester.target_text_for(row), "Target: 200 ms or less")
        self.assertNotIn("needs improvement", site_tester.target_text_for(row))

    def test_interpretation_follows_metrics_and_precedes_recommendations(self):
        app = AppTest.from_function(recommendation_preview).run(timeout=20)
        self.assertFalse(app.exception)
        elements = list(app.main)
        metric_indexes = [
            index
            for index, element in enumerate(elements)
            if element.type == "markdown" and "compact-metric" in element.value
        ]
        meaning_index = next(
            index
            for index, element in enumerate(elements)
            if element.type == "html" and "meaning-card" in element.proto.body
        )
        recommendations_index = next(
            index
            for index, element in enumerate(elements)
            if element.type == "html"
            and '<h2 class="recommendations-heading">What to Fix First</h2>' in element.proto.body
        )

        self.assertLess(max(metric_indexes), meaning_index)
        self.assertLess(meaning_index, recommendations_index)

    def test_missing_measurements_are_not_reported_as_healthy(self):
        with patch.object(site_tester.st, "info") as info:
            site_tester.render_action_plan({}, [], [], "Other / Not sure")
        self.assertIn("Unavailable measurements are not a passing result", info.call_args.args[0])

    def test_shared_renderer_escapes_dynamic_content(self):
        rows = site_tester.build_field_metric_rows({"field_largest-contentful-paint": 9000})
        issue = site_tester.build_priority_issues([], rows)[0]
        issue["Metric"] = '<script>alert("test")</script>'
        with patch.object(site_tester.st, "html") as html_renderer:
            site_tester.render_recommendation_card(issue, {}, "WordPress", rank=1)
        rendered = html_renderer.call_args.args[0]
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("Highest priority", rendered)

    def test_supporting_actions_are_visible_and_structured(self):
        app = AppTest.from_function(recommendation_preview).run(timeout=20)
        self.assertFalse(app.exception)
        cards = [item.proto.body for item in app.get("html") if '<article class="priority-card secondary-fix"' in item.proto.body]
        self.assertEqual(len(cards), 2)
        for rank, card in enumerate(cards, start=2):
            with self.subTest(rank=rank):
                self.assertNotIn("<details", card)
                self.assertNotIn("<summary", card)
                self.assertIn(f"Priority {rank}", card)
                self.assertIn('<h4 class="priority-title">', card)
                self.assertIn('class="priority-value ', card)
                self.assertIn('class="priority-target"', card)
                self.assertIn('class="priority-fix-title"', card)
                self.assertIn("Start with this", card)
                self.assertIn("Prefer someone to fix it?", card)
                self.assertIn("For your developer:", card)
                self.assertIn('rel="noopener"', card)
        self.assertIn("Find what makes the content move", cards[0])
        self.assertIn("Check apps, popups, and interactive tools", cards[1])
        self.assertNotIn("Follow these steps:", cards[0])
        self.assertIn("Follow these steps: Manage WordPress plugins", cards[1])

    def test_owner_actions_and_guide_precede_supporting_measurements(self):
        lab, field = audit_rows({"field_largest-contentful-paint": 9000})
        issue = site_tester.build_priority_issues(lab, field, "URL")[0]
        with patch.object(site_tester.st, "html") as renderer:
            site_tester.render_recommendation_card(
                issue, {"image-delivery-insight_savings_bytes": 500000}, "WordPress", 1,
            )
        card = renderer.call_args.args[0]
        self.assertIn("Main content takes too long to appear", card)
        self.assertIn("Visitors may wait longer", card)
        self.assertLess(card.index("Start with this"), card.index("Follow these steps:"))
        self.assertLess(card.index("Follow these steps:"), card.index("Prefer someone to fix it?"))
        self.assertLess(card.index("Prefer someone to fix it?"), card.index("Supporting evidence"))
        self.assertIn("Largest Contentful Paint (LCP)", card)
        self.assertIn("potential transfer savings", card)

    def test_owner_explanation_keeps_lab_risk_and_field_scope_distinct(self):
        lab, field = audit_rows({"total-blocking-time": 800, "INTERACTION_TO_NEXT_PAINT": 400})
        lab_issue = site_tester.build_priority_issues(lab, [])[0]
        self.assertIn("warning sign", site_tester.visitor_impact_for(lab_issue))
        self.assertIn("not a measurement of actual visitor response times", site_tester.visitor_impact_for(lab_issue))
        for scope in ("URL", "Origin", None):
            issue = site_tester.build_priority_issues([], field, scope)[0]
            impact = site_tester.visitor_impact_for(issue)
            self.assertIn("delay after clicking", impact)
            if scope == "Origin":
                self.assertIn("check whether this happens on this page", impact)
            elif scope is None:
                self.assertIn("cannot tell", impact)
            else:
                self.assertNotIn("website overall", impact)

    def test_cards_bypass_markdown(self):
        rows = site_tester.build_field_metric_rows({"field_largest-contentful-paint": 9000})
        issue = site_tester.build_priority_issues([], rows)[0]
        for rank in (1, 2, 3):
            with (
                self.subTest(rank=rank),
                patch.object(site_tester.st, "html") as html_renderer,
                patch.object(site_tester.st, "markdown") as markdown,
            ):
                site_tester.render_recommendation_card(issue, {}, "WordPress", rank=rank)
                html_renderer.assert_called_once()
                markdown.assert_not_called()
                self.assertIn(f'aria-label="Recommendation {rank}"', html_renderer.call_args.args[0])

    def test_lab_cards_use_html_renderer(self):
        app = AppTest.from_function(recommendation_preview).run(timeout=20)
        app.selectbox[0].set_value("Lab")
        app.selectbox[1].set_value("Shopify")
        app.run(timeout=20)
        self.assertFalse(app.exception)
        cards = [item for item in app.get("html") if "<article " in item.proto.body]
        self.assertEqual(len(cards), 3)
        for card in cards:
            self.assertFalse(card.proto.unsafe_allow_javascript)
            self.assertIn('class="priority-fix"', card.proto.body)
            self.assertNotIn("Shopify performance help", card.proto.body)
        self.assertIn("The page may be slow to respond", cards[0].proto.body)
        self.assertFalse(any("<article " in item.value for item in app.markdown))

    def test_general_cms_help_is_shown_once_below_selector(self):
        app = AppTest.from_function(recommendation_preview).run(timeout=20)
        for platform in PLATFORM_OPTIONS:
            with self.subTest(platform=platform):
                app.selectbox[1].set_value(platform).run(timeout=20)
                self.assertFalse(app.exception)
                output = [item.proto.body for item in app.get("html")]
                cards = [body for body in output if "<article " in body]
                shared_help = [body for body in output if 'class="platform-help"' in body]
                self.assertEqual(len(cards), 3)
                support = PLATFORM_SUPPORT.get(platform)
                if support:
                    self.assertEqual("".join(output).count(support["url"]), 1)
                    self.assertIn(support["label"], "".join(output))
                self.assertTrue(any("previous 28 days" in item.value for item in app.markdown))
                self.assertTrue(any("Get help with these fixes" in item.value for item in app.markdown))
                for card in cards:
                    self.assertIn("For your developer:", card)
                if platform in PLATFORM_HELP:
                    general_url = PLATFORM_HELP[platform]["url"]
                    self.assertEqual(len(shared_help), 1)
                    self.assertEqual("".join(output).count(general_url), 1)
                    self.assertTrue(all(general_url not in card for card in cards))
                    self.assertIn(f"General {platform} performance guide", shared_help[0])
                    elements = list(app.main)
                    selector_index = next(
                        index for index, element in enumerate(elements)
                        if element.type == "selectbox" and element.key == "website_platform"
                    )
                    self.assertEqual(elements[selector_index + 1].type, "html")
                    self.assertEqual(elements[selector_index + 1].proto.body, shared_help[0])
                    self.assertLess(output.index(shared_help[0]), output.index(cards[0]))
                else:
                    self.assertFalse(shared_help)


if __name__ == "__main__":
    # Browser check: streamlit run tests/test_recommendation_cards.py -- --preview
    if "--preview" in sys.argv:
        recommendation_preview()
    else:
        unittest.main()
