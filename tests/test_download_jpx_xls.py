#!/usr/bin/env python3
"""
Tests for download_jpx_xls()'s temp-file suffix derivation in
bin/update_delisted_companies.py (issue #227).

The suffix must be derived from the URL's path component so a query string
or fragment on a custom --source-url never leaks into the temp-file suffix
(openpyxl re-derives the extension from the filename and rejects anything
that isn't literally .xlsx/.xlsm/.xltx/.xltm).
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path so `bin.*` imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.update_delisted_companies import download_jpx_xls  # noqa: E402


def _fake_response(content: bytes = b"dummy-bytes"):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.content = content
    response.headers.get.return_value = "application/octet-stream"
    return response


class TestDownloadJpxXlsSuffix(unittest.TestCase):

    def _download_and_cleanup(self, url: str) -> str:
        """Download to a temp path, return its suffix, and delete the file."""
        with patch("bin.update_delisted_companies.requests.get", return_value=_fake_response()):
            path = download_jpx_xls(url)
        try:
            return os.path.splitext(path)[1]
        finally:
            os.remove(path)

    def test_suffix_matches_plain_xlsx_url(self):
        suffix = self._download_and_cleanup("https://example.com/data_j.xlsx")
        self.assertEqual(suffix, ".xlsx")

    def test_suffix_ignores_query_string(self):
        # Regression for issue #227 review: os.path.splitext(url) on the raw
        # URL would previously return ".xlsx?token=abc" as the "extension".
        suffix = self._download_and_cleanup("https://example.com/data_j.xlsx?token=abc&x=1")
        self.assertEqual(suffix, ".xlsx")

    def test_suffix_falls_back_to_xlsx_when_path_has_no_extension(self):
        # A bare-domain URL has an empty path, so splitext(urlparse(url).path)
        # yields no extension and the ".xlsx" fallback applies.
        suffix = self._download_and_cleanup("https://example.com")
        self.assertEqual(suffix, ".xlsx")

    def test_suffix_follows_custom_source_url_extension(self):
        suffix = self._download_and_cleanup("https://example.com/listing.csv")
        self.assertEqual(suffix, ".csv")


if __name__ == "__main__":
    unittest.main()
