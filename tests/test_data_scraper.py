"""
Tests for the requests + BeautifulSoup market-data fetcher (issue #185, PR4).

All tests run offline against saved HTML fixtures (synthetic values, real DOM
structure) - no live network. The parser is anchored on the Japanese label
"時価総額" and the semantic price-board class fragment, both verified against the
real Yahoo SSR page.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import data_scraper
from lib.data_scraper import get_financial_data, parse_market_data
from lib.xbrl_parser import MetricsCalculator

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as f:
        return f.read()


class TestParseMarketData(unittest.TestCase):
    """Criterion 3: parse stockPrice and marketCapitalization (yen) from saved HTML."""

    def test_parses_price_and_market_cap(self):
        data = parse_market_data(_fixture("yahoo_quote_sample.html"))
        self.assertEqual(data["stockPrice"], 1234.0)
        # 9,999 百万円 -> 9,999,000,000 yen
        self.assertEqual(data["marketCapitalization"], 9999000000)

    def test_empty_page_yields_none(self):
        data = parse_market_data(_fixture("yahoo_quote_empty.html"))
        self.assertIsNone(data["stockPrice"])
        self.assertIsNone(data["marketCapitalization"])

    def test_isolates_price_and_unit_with_sibling_figures_and_class_drift(self):
        """A different hash suffix, sibling price-board figures (前日終値, a change
        figure) and an adjacent 円-denominated metric must not be mistaken for the
        current price or corrupt the 時価総額 unit."""
        data = parse_market_data(_fixture("yahoo_quote_drift.html"))
        self.assertEqual(data["stockPrice"], 5678.0)         # not 前日終値 5,700 / change -12
        self.assertEqual(data["marketCapitalization"], 8888000000)  # 8,888 百万円, not the 円 metric


class TestMarketCapUnit(unittest.TestCase):
    def test_missing_unit_warns_and_assumes_millions(self):
        html = (
            '<ul><li class="_DataListItem_x_1">'
            '<span class="_DataListItem__name_x_19">時価総額</span>'
            '<span class="_DataListItem__data_x_40">'
            '<span class="_StyledNumber__value_x_9">7,000</span></span>'
            '</li></ul>'
        )
        with self.assertLogs("lib.data_scraper", level="WARNING") as cm:
            data = parse_market_data(html)
        self.assertEqual(data["marketCapitalization"], 7_000_000_000)  # assumed 百万円
        self.assertIn("時価総額", "\n".join(cm.output))


class TestGetFinancialData(unittest.TestCase):
    def setUp(self):
        data_scraper.reset_market_null_counts()

    @patch("lib.data_scraper._fetch_html")
    def test_returns_market_data_only(self, mock_fetch):
        mock_fetch.return_value = _fixture("yahoo_quote_sample.html")
        result = get_financial_data("9999", "2025年3月期")
        self.assertEqual(set(result.keys()), {"stockPrice", "marketCapitalization"})
        self.assertEqual(result["stockPrice"], 1234.0)
        self.assertEqual(result["marketCapitalization"], 9999000000)

    @patch("lib.data_scraper._fetch_html")
    def test_null_when_no_market_data_and_warns(self, mock_fetch):
        """Criterion 4: empty page -> market fields null + WARNING naming them."""
        mock_fetch.return_value = _fixture("yahoo_quote_empty.html")
        with self.assertLogs("lib.data_scraper", level="WARNING") as cm:
            result = get_financial_data("9999", "2025年3月期")
        self.assertIsNone(result["stockPrice"])
        self.assertIsNone(result["marketCapitalization"])
        joined = "\n".join(cm.output)
        self.assertIn("stockPrice", joined)
        self.assertIn("marketCapitalization", joined)
        self.assertEqual(data_scraper.market_null_counts["stockPrice"], 1)
        self.assertEqual(data_scraper.market_null_counts["marketCapitalization"], 1)

    @patch("lib.data_scraper._fetch_html")
    def test_null_when_fetch_fails(self, mock_fetch):
        mock_fetch.return_value = None
        with self.assertLogs("lib.data_scraper", level="WARNING"):
            result = get_financial_data("9999", "2025年3月期")
        self.assertIsNone(result["stockPrice"])
        self.assertIsNone(result["marketCapitalization"])
        self.assertEqual(data_scraper.market_null_counts["stockPrice"], 1)


class TestMarketDrivenMetrics(unittest.TestCase):
    """Criterion 3: per/pbr are computed as stockPrice/eps and stockPrice/bps
    from XBRL inputs; marketCap prefers the fetched value."""

    def test_per_pbr_and_market_cap_preference(self):
        market = parse_market_data(_fixture("yahoo_quote_sample.html"))  # stockPrice 1234
        data = {
            "stockPrice": market["stockPrice"],
            "marketCapitalization": market["marketCapitalization"],
            "eps": 100.0,   # as if extracted from XBRL
            "bps": 500.0,   # as if extracted from XBRL
            "outstandingShares": 7,  # would give a different (wrong) market cap if used
        }
        result = MetricsCalculator.calculate_derived_metrics(data)
        self.assertAlmostEqual(result["per"], 1234.0 / 100.0)
        self.assertAlmostEqual(result["pbr"], 1234.0 / 500.0)
        # marketCap keeps the fetched value, not shares*price
        self.assertEqual(result["marketCapitalization"], 9999000000)

    def test_market_cap_falls_back_to_shares_times_price(self):
        data = {
            "stockPrice": 1000.0,
            "marketCapitalization": None,  # fetcher supplied nothing
            "outstandingShares": 10000,
        }
        result = MetricsCalculator.calculate_derived_metrics(data)
        self.assertEqual(result["marketCapitalization"], 10000 * 1000.0)


if __name__ == "__main__":
    unittest.main()
