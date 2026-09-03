import sys
import unittest
from pathlib import Path


DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "src" / "dashboard"
sys.path.insert(0, str(DASHBOARD_PATH))

from utils.platform_guidance import detect_platform, guidance_for


class PlatformGuidanceTest(unittest.TestCase):
    def test_detects_platform_from_lighthouse_requests(self):
        audits = {
            "network-requests": {
                "details": {
                    "items": [
                        {"url": "https://example.com/assets/site.css"},
                        {"url": "https://cdn.shopify.com/theme.js"},
                    ]
                }
            }
        }

        self.assertEqual(detect_platform(audits), "Shopify")

    def test_unknown_platform_uses_generic_guidance(self):
        self.assertIsNone(detect_platform({"network-requests": {"details": None}}))

        guidance = guidance_for("Other / Not sure", "images")

        self.assertIn("site editor", guidance["owner_action"])
        self.assertIsNone(guidance["resource_url"])

    def test_supported_platform_uses_specific_guidance(self):
        guidance = guidance_for("Shopify", "server")

        self.assertIn("Shopify manages", guidance["owner_action"])
        self.assertIn("shopify.com", guidance["resource_url"])

    def test_help_links_match_platform_and_recommended_action(self):
        cases = [
            ("WordPress", "lcp", "https://learn.wordpress.org/lesson/website-optimization/"),
            ("WordPress", "images", "https://learn.wordpress.org/lesson/image-optimization/"),
            ("Wix", "images", "https://support.wix.com/en/article/site-performance-optimizing-your-media"),
            ("Wix", "javascript", "https://support.wix.com/en/article/site-performance-best-practices"),
            ("Shopify", "images", "https://help.shopify.com/en/manual/online-store/web-performance/improving-web-performance"),
            ("Squarespace", "images", "https://support.squarespace.com/hc/en-us/articles/360022529371-Reducing-your-page-size-for-faster-loading"),
            ("Squarespace", "lcp", "https://support.squarespace.com/hc/en-us/articles/360022529371-Reducing-your-page-size-for-faster-loading"),
            ("Squarespace", "server", "https://support.squarespace.com/hc/en-us/articles/206545657-My-site-is-loading-slowly"),
            ("Squarespace", "javascript", "https://support.squarespace.com/hc/en-us/articles/206545657-My-site-is-loading-slowly"),
        ]
        for platform, fix_id, expected_url in cases:
            with self.subTest(platform=platform, fix_id=fix_id):
                guidance = guidance_for(platform, fix_id)
                self.assertEqual(guidance["resource_url"], expected_url)
                self.assertTrue(guidance["resource_label"])


if __name__ == "__main__":
    unittest.main()
