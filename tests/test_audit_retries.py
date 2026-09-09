"""Deterministic failure checks without live PSI calls."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[1] / "src/dashboard"
sys.path.insert(0, str(DASHBOARD))
from utils import fetch_lighthouse_data as fetcher


def response(data, status=200):
    return Mock(ok=status < 400, status_code=status, json=Mock(return_value=data))


GOOD = {"lighthouseResult": {"audits": {
    "largest-contentful-paint": {"numericValue": 3000},
    "cumulative-layout-shift": {"numericValue": 0},
}}}
FAILED = {"lighthouseResult": {"runtimeError": {"code": "NO_FCP", "message": "No content painted"},
    "audits": GOOD["lighthouseResult"]["audits"]}}
FIELD = {"loadingExperience": {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2800}}}}


class AuditRetryTest(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(fetcher.os.environ, {"API_KEY": ""})
        environment.start()
        self.addCleanup(environment.stop)
        sleeper = patch.object(fetcher.time, "sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def fetch(self, responses):
        with patch.object(fetcher.requests, "get", side_effect=responses) as get:
            result = fetcher.fetch_data("https://example.com", "desktop", api_key="test-secret")
        self.assertLessEqual(get.call_count, 2)
        return result, get

    def test_transient_failures_recover_once(self):
        for failure in (
            response(FAILED), response({"error": {"message": "Lighthouse returned error: Something went wrong."}}, 500),
            response({}, 429), response({}), response([]), requests.Timeout("test-secret"),
            requests.ConnectionError("test-secret"),
            Mock(ok=True, json=Mock(side_effect=ValueError("bad json"))),
        ):
            with self.subTest(failure=failure):
                result, get = self.fetch([failure, response(GOOD)])
                self.assertEqual(get.call_count, 2)
                self.assertEqual(result["largest-contentful-paint"], 3000)
                self.assertNotIn("lab_error", result)
                self.assertEqual(get.call_args_list[0], get.call_args_list[1])

    def test_repeated_failure_is_not_a_completed_audit(self):
        result, get = self.fetch([response(FAILED), response(FAILED)])
        self.assertEqual(get.call_count, 2)
        self.assertIn("error", result)
        self.assertNotIn("largest-contentful-paint", result)

    def test_partial_field_data_survives_failed_retry_without_bad_lab_evidence(self):
        for second in (requests.Timeout(), response(FAILED)):
            result, _ = self.fetch([response({**FAILED, **FIELD}), second])
            self.assertEqual(result["field_largest-contentful-paint"], 2800)
            self.assertIsNone(result["largest-contentful-paint"])
            self.assertIsNone(result["performance_score"])
            self.assertIn("lab_error", result)
            self.assertNotIn("error", result)
            self.assertFalse(any(result["audit_items"].values()))

    def test_permanent_errors_and_success_do_not_retry(self):
        for data, status in ((GOOD, 200), ({"error": {"message": "Invalid URL"}}, 400),
                             ({"error": {"message": "API key invalid"}}, 403)):
            _, get = self.fetch([response(data, status)])
            self.assertEqual(get.call_count, 1)
        self.sleep.assert_not_called()

    def test_partial_lab_report_is_still_usable(self):
        result, get = self.fetch([response({"lighthouseResult": {"audits": {
            "cumulative-layout-shift": {"numericValue": 0.2},
        }}})])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(result["cumulative-layout-shift"], 0.2)
        self.assertNotIn("error", result)

    def test_api_key_sources(self):
        for explicit, environment, secrets, expected in (
            (None, {"API_KEY": "railway-key"}, {}, "railway-key"),
            (None, {}, {"API_KEY": "streamlit-key"}, "streamlit-key"),
            ("explicit-key", {"API_KEY": "railway-key"}, {}, "explicit-key"),
        ):
            with self.subTest(source=expected), patch.dict(fetcher.os.environ, {"API_KEY": "", **environment}), \
                    patch.object(fetcher.st, "secrets", secrets), \
                    patch.object(fetcher, "_fetch_attempt", return_value=({}, False)) as attempt:
                fetcher.fetch_data("https://example.com", "mobile", api_key=explicit)
                attempt.assert_called_once_with("https://example.com", "mobile", expected)

    def test_missing_key_and_logs_are_safe(self):
        with patch.object(fetcher.st, "secrets", {}), patch.object(fetcher.requests, "get") as get:
            self.assertIn("error", fetcher.fetch_data("https://example.com", "mobile"))
            get.assert_not_called()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result, _ = self.fetch([response({"error": {"message": "test-secret"}}, 403)])
        self.assertNotIn("test-secret", output.getvalue())
        self.assertNotIn("test-secret", str(result))

    def test_retry_button_remembers_url_and_device(self):
        with patch.object(fetcher, "fetch_data", side_effect=[
            {"error": "The test could not finish. Please try again."},
            {"largest-contentful-paint": 3000},
        ]) as fetch:
            app = AppTest.from_file(str(DASHBOARD / "app.py")).run(timeout=20)
            app.text_input[0].set_value("example.com")
            app.radio[0].set_value("Desktop")
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertFalse(app.session_state["website_submitted"])
            retry_app = AppTest.from_file(str(DASHBOARD / "app.py"))
            for key in ("audit_error", "last_audit", "last_website_input"):
                retry_app.session_state[key] = app.session_state[key]
            retry_app.run(timeout=20)
            next(button for button in retry_app.button if button.label == "Try again").click().run(timeout=20)
            self.assertFalse(retry_app.exception)
            self.assertTrue(retry_app.session_state["website_submitted"])
            self.assertEqual(fetch.call_args_list[0], fetch.call_args_list[1])
            self.assertEqual(fetch.call_args.args, ("https://example.com", "desktop"))

    def test_partial_results_remain_visible_when_manual_retry_fails(self):
        partial, _ = self.fetch([response({**FAILED, **FIELD}), response(FAILED)])
        app = AppTest.from_file(str(DASHBOARD / "app.py"))
        for key, value in {
            "website_submitted": True, "result": partial,
            "website": "https://example.com", "strategy": "Desktop",
            "last_audit": ("https://example.com", "Desktop"),
            "website_platform": "Other / Not sure",
        }.items():
            app.session_state[key] = value
        with patch.object(fetcher, "fetch_data", return_value={"error": "The test could not finish."}) as fetch:
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertFalse(app.success)
            next(button for button in app.button if button.label == "Try again").click().run(timeout=20)
            self.assertFalse(app.exception)
            fetch.assert_called_once_with("https://example.com", "desktop")
            self.assertTrue(app.session_state["website_submitted"])
            self.assertEqual(app.session_state["result"]["field_largest-contentful-paint"], 2800)
            self.assertTrue(any("earlier real-user results" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
