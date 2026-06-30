"""
Sequential market-fetch behaviour across multiple companies (issue #185).

The Playwright batch API (`get_financial_data_batch`) was removed; companies are
fetched one at a time through `get_financial_data` on a shared, paced session.
These tests run offline against saved HTML fixtures and assert the run-summary
null counters accumulate correctly across a mix of success / empty / failure.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import data_scraper
from lib.data_scraper import get_financial_data

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as f:
        return f.read()


class TestSequentialFetch(unittest.TestCase):
    def setUp(self):
        data_scraper.reset_market_null_counts()

    @patch("lib.data_scraper._fetch_html")
    def test_null_counters_accumulate_across_companies(self, mock_fetch):
        # One good page, one soft-blocked empty page, one outright fetch failure.
        mock_fetch.side_effect = [
            _fixture("yahoo_quote_sample.html"),
            _fixture("yahoo_quote_empty.html"),
            None,
        ]
        results = [get_financial_data(code, "2025年3月期") for code in ("1111", "2222", "3333")]

        # The good company has values; the other two are null.
        self.assertEqual(results[0]["stockPrice"], 1234.0)
        self.assertIsNone(results[1]["stockPrice"])
        self.assertIsNone(results[2]["stockPrice"])

        # Two of three companies lacked each market field.
        self.assertEqual(data_scraper.market_null_counts["stockPrice"], 2)
        self.assertEqual(data_scraper.market_null_counts["marketCapitalization"], 2)

    @patch("lib.data_scraper._fetch_html")
    def test_one_company_failure_does_not_abort_the_rest(self, mock_fetch):
        mock_fetch.side_effect = [None, _fixture("yahoo_quote_sample.html")]
        first = get_financial_data("1111", "2025年3月期")
        second = get_financial_data("2222", "2025年3月期")
        self.assertIsNone(first["stockPrice"])
        self.assertEqual(second["stockPrice"], 1234.0)


if __name__ == "__main__":
    unittest.main()
