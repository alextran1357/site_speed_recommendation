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


if __name__ == "__main__":
    unittest.main()
