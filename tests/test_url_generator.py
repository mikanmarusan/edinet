import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.url_generator import generate_yahoo_finance_url


class TestURLGenerator(unittest.TestCase):
    """The market fetcher now uses only the single SSR base quote URL (issue #185)."""

    BASE = "https://finance.yahoo.co.jp/quote/"

    def test_generate_url_basic(self):
        self.assertEqual(generate_yahoo_finance_url("7203.T"), f"{self.BASE}7203.T")

    def test_generate_url_different_exchanges(self):
        for ticker in ["7203.T", "2413.N", "3382.S", "6701.F"]:
            with self.subTest(ticker=ticker):
                url = generate_yahoo_finance_url(ticker)
                self.assertEqual(url, f"{self.BASE}{ticker}")
                self.assertIn(ticker, url)

    def test_generate_url_various_formats(self):
        for ticker in ["1234", "1234.T", "12345.T", "123.T", "1.T"]:
            with self.subTest(ticker=ticker):
                url = generate_yahoo_finance_url(ticker)
                self.assertEqual(url, f"{self.BASE}{ticker}")

    def test_url_format_consistency(self):
        url = generate_yahoo_finance_url("9984.T")
        self.assertTrue(url.startswith("https://"))
        self.assertIn("finance.yahoo.co.jp", url)
        # No sub-path / query params: only the base quote page is fetched now.
        self.assertNotIn("?", url)
        self.assertFalse(url.endswith("/profile"))

    def test_return_type(self):
        result = generate_yahoo_finance_url("7203.T")
        self.assertIsInstance(result, str)

    def test_empty_ticker(self):
        self.assertEqual(generate_yahoo_finance_url(""), self.BASE)


if __name__ == '__main__':
    unittest.main()
