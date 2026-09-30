#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

from serve_html import is_same_origin_local_request


class LocalServerAuthorizationTest(unittest.TestCase):
    def test_local_page_is_allowed_by_browser_fetch_metadata(self) -> None:
        self.assertTrue(
            is_same_origin_local_request(
                {
                    "Host": "127.0.0.1:8765",
                    "Sec-Fetch-Site": "same-origin",
                    "Referer": "http://127.0.0.1:8765/ask.html",
                }
            )
        )

    def test_local_page_is_allowed_by_referer(self) -> None:
        self.assertTrue(
            is_same_origin_local_request(
                {
                    "Host": "localhost:8765",
                    "Referer": "http://localhost:8765/ask.html",
                }
            )
        )

    def test_cross_site_request_is_rejected(self) -> None:
        self.assertFalse(
            is_same_origin_local_request(
                {
                    "Host": "127.0.0.1:8765",
                    "Origin": "https://example.com",
                    "Sec-Fetch-Site": "cross-site",
                }
            )
        )

    def test_file_page_without_token_is_rejected(self) -> None:
        self.assertFalse(
            is_same_origin_local_request(
                {
                    "Host": "127.0.0.1:8765",
                    "Origin": "null",
                    "Sec-Fetch-Site": "cross-site",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
