from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, override_settings

from calendars.subscription_fetch import fetch_subscription


@override_settings(ICAL_ALLOWED_ORIGINS=["https://calendar.example.com"])
class SubscriptionFetchTests(SimpleTestCase):
    def test_unapproved_urls_never_connect(self):
        for url in ["http://calendar.example.com/feed", "https://127.0.0.1/",
                    "https://calendar.example.com.evil.test/feed",
                    "https://calendar.example.com:8443/feed",
                    "https://user:pass@calendar.example.com/feed"]:
            with self.subTest(url=url), patch("httpx.Client") as client:
                with self.assertRaises(ValueError):
                    fetch_subscription(url)
                client.assert_not_called()

    def mocked_client(self, status=200, content=b"BEGIN:VCALENDAR", headers=None):
        response = httpx.Response(status, content=content, headers=headers,
                                  request=httpx.Request("GET", "https://calendar.example.com/feed"))
        return httpx.Client(transport=httpx.MockTransport(lambda request: response))

    def test_successful_feed(self):
        with patch("httpx.Client", return_value=self.mocked_client()):
            self.assertEqual(fetch_subscription("https://calendar.example.com/feed").text,
                             "BEGIN:VCALENDAR")

    def test_redirect_is_rejected(self):
        with patch("httpx.Client", return_value=self.mocked_client(
                302, headers={"Location": "http://169.254.169.254/"})):
            with self.assertRaises(httpx.HTTPStatusError):
                fetch_subscription("https://calendar.example.com/feed")

    def test_feed_size_is_bounded(self):
        with patch("calendars.subscription_fetch.MAX_FEED_BYTES", 3), patch(
                "httpx.Client", return_value=self.mocked_client(content=b"1234")):
            with self.assertRaises(ValueError):
                fetch_subscription("https://calendar.example.com/feed")

    def test_not_modified(self):
        with patch("httpx.Client", return_value=self.mocked_client(304, content=b"")):
            self.assertEqual(fetch_subscription("https://calendar.example.com/feed", '"v1"').status_code, 304)
