import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))


def recommendation_preview():
    import streamlit as st
    from modules.site_tester import (
        build_field_metric_rows,
        inject_dashboard_styles,
        render_action_plan,
    )

    st.set_page_config(layout="centered")
    inject_dashboard_styles()
    result = {
        "field_largest-contentful-paint": 9000,
        "field_cumulative-layout-shift": 0.3,
        "INTERACTION_TO_NEXT_PAINT": 350,
    }
    render_action_plan(result, [], build_field_metric_rows(result), "WordPress")


class RecommendationCardsTest(unittest.TestCase):
    def test_supporting_actions_are_visible_and_structured(self):
        app = AppTest.from_function(recommendation_preview).run(timeout=20)
        self.assertFalse(app.exception)
        cards = [item.value for item in app.markdown if '<article class="priority-card secondary-fix"' in item.value]
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


if __name__ == "__main__":
    unittest.main()
