import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))

from modules import site_tester
from utils.platform_guidance import PLATFORM_HELP, PLATFORM_OPTIONS


def recommendation_preview():
    import streamlit as st
    from modules.site_tester import (
        inject_dashboard_styles,
        load_component,
    )
    from utils.data_loader import load_data

    st.set_page_config(layout="centered")
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
    st.session_state.result = result
    st.session_state.strategy = "Mobile"
    load_component(load_data())


class RecommendationCardsTest(unittest.TestCase):
    def test_interpretation_explains_when_field_data_is_better_than_lab_data(self):
        interpretation = site_tester.results_interpretation(
            [{"Status": "Poor"}, {"Status": "Needs improvement"}],
            [{"Status": "Good"}, {"Status": "Good"}, {"Status": "Good"}],
        )

        self.assertEqual(interpretation["tone"], "mixed")
        self.assertEqual(interpretation["title"], "Real users look better than this lab test")
        self.assertIn("Trust the 28-day field data", interpretation["body"])
        self.assertNotIn("context", interpretation)

    def test_interpretation_does_not_treat_missing_field_data_as_healthy(self):
        interpretation = site_tester.results_interpretation(
            [{"Status": "Poor"}],
            [{"Status": "Unavailable"}],
        )

        self.assertEqual(interpretation["tone"], "caution")
        self.assertEqual(interpretation["title"], "Only the lab test is available")
        self.assertIn("not enough real-user data", interpretation["body"])

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
                self.assertIn("What you can try", card)
                self.assertIn("When to get help", card)
                self.assertIn("For your developer:", card)
                self.assertIn('rel="noopener"', card)
        self.assertIn("Reserve space for elements that shift", cards[0])
        self.assertIn("Investigate long main-thread tasks", cards[1])
        self.assertNotIn("Follow these steps:", cards[0])
        self.assertIn("Follow these steps: Manage WordPress plugins", cards[1])

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
        self.assertIn("Responsiveness risk (TBT)", cards[0].proto.body)
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
