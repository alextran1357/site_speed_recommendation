import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))

from modules import site_tester


def recommendation_preview():
    import streamlit as st
    from modules.site_tester import (
        build_field_metric_rows,
        build_metric_rows,
        inject_dashboard_styles,
        render_action_plan,
    )
    from utils.data_loader import load_data
    from utils.platform_guidance import PLATFORM_OPTIONS

    st.set_page_config(layout="centered")
    inject_dashboard_styles()
    source = st.selectbox("Measurement source", ["Field", "Lab"])
    platform = st.selectbox("Website platform", PLATFORM_OPTIONS)
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
    metric_rows = (
        build_metric_rows(result, load_data(), "mobile", None, "All sites")
        if source == "Lab" else []
    )
    render_action_plan(result, metric_rows, build_field_metric_rows(result), platform)


class RecommendationCardsTest(unittest.TestCase):
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
                self.assertIn("Follow these steps:", card)
                self.assertIn("For your developer:", card)
                self.assertIn('rel="noopener"', card)
        self.assertIn("Reserve space for elements that shift", cards[0])
        self.assertIn("Investigate long main-thread tasks", cards[1])

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
        cards = app.get("html")
        self.assertEqual(len(cards), 3)
        for card in cards:
            self.assertFalse(card.proto.unsafe_allow_javascript)
            self.assertIn('class="priority-fix"', card.proto.body)
            self.assertIn("Shopify performance help", card.proto.body)
        self.assertIn("Responsiveness risk (TBT)", cards[0].proto.body)
        self.assertFalse(any("<article " in item.value for item in app.markdown))


if __name__ == "__main__":
    # Browser check: streamlit run tests/test_recommendation_cards.py -- --preview
    if "--preview" in sys.argv:
        recommendation_preview()
    else:
        unittest.main()
