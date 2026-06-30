import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from datetime import datetime
import json
import zipfile
import io

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.xbrl_parser import XBRLParser
from lib.data_scraper import get_financial_data


# All fixtures use a fictitious company with synthetic, obviously-fake round
# numbers - never a real filer's figures. These are round-trip tests: a value is
# placed in the fixture (Yahoo dict or XBRL body) and asserted to come back out;
# they validate sourcing/wiring, not any real company's reported values.
SEC_CODE = "9999"
FILER_NAME = "テスト製造株式会社"
DOC_ID = "S100TEST"
STOCK_PRICE = 1000.0
EQUITY = 5000000000
CASH = 1200000000


class TestYahooFinanceIntegration(unittest.TestCase):
    """Test integration between Yahoo Finance and XBRL data processing"""

    def setUp(self):
        """Set up test fixtures"""
        self.xbrl_parser = XBRLParser()

        # Synthetic market-fetcher data for the fictitious company.
        self.yahoo_data = {
            'stockPrice': STOCK_PRICE,
            'characteristic': 'テスト企業の事業概要',
            'employees': 1000,
            'netSales': 8000000000,
            'operatingIncome': 900000000,
            'ordinaryIncome': 850000000,
            'netIncome': 600000000,
            'eps': 60.0,
            'bps': 500.0,
            'depreciation': 300000000,
            'outstandingShares': 10000000,
            'debt': 2000000000
        }

        # Sample XBRL content (minimal valid structure, synthetic values)
        xbrl_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-03-31/jppfs_cor">
            <context id="CurrentYearInstant">
                <entity>
                    <identifier scheme="http://disclosure.edinet-fsa.go.jp">9999</identifier>
                </entity>
                <period>
                    <instant>2023-03-31</instant>
                </period>
            </context>
            <context id="CurrentYearDuration">
                <entity>
                    <identifier scheme="http://disclosure.edinet-fsa.go.jp">9999</identifier>
                </entity>
                <period>
                    <startDate>2022-04-01</startDate>
                    <endDate>2023-03-31</endDate>
                </period>
            </context>
            <unit id="JPY">
                <measure>http://www.xbrl.org/2003/iso4217:JPY</measure>
            </unit>
            <jppfs_cor:Equity contextRef="CurrentYearInstant" unitRef="JPY" decimals="-6">5000000000</jppfs_cor:Equity>
            <jppfs_cor:CashAndCashEquivalents contextRef="CurrentYearInstant" unitRef="JPY" decimals="-6">1200000000</jppfs_cor:CashAndCashEquivalents>
        </xbrl>"""

        # Create a ZIP file containing the XBRL content
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('PublicDoc/document.xbrl', xbrl_xml)
        self.xbrl_content = zip_buffer.getvalue()

    def test_xbrl_parser_with_yahoo_data(self):
        """Test that XBRL parser correctly integrates Yahoo Finance data"""
        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=self.yahoo_data
        )

        # Only stockPrice still comes from the market fetcher (issue #184 moved
        # ordinaryIncome and debt to XBRL).
        self.assertIsNotNone(result)
        self.assertEqual(result['stockPrice'], STOCK_PRICE)

        # Financial-statement fields are now sourced from XBRL, not Yahoo; this
        # fixture's XBRL omits them, so they are None regardless of yahoo_data.
        self.assertIsNone(result['characteristic'])
        self.assertIsNone(result['employees'])
        self.assertIsNone(result['netSales'])
        self.assertIsNone(result['operatingIncome'])
        self.assertIsNone(result['ordinaryIncome'])
        self.assertIsNone(result['netIncome'])
        self.assertIsNone(result['eps'])
        self.assertIsNone(result['bps'])
        self.assertIsNone(result['debt'])

        # Verify that XBRL data is still extracted
        self.assertEqual(result['equity'], EQUITY)
        self.assertEqual(result['cash'], CASH)

        # Verify metadata
        self.assertEqual(result['secCode'], SEC_CODE)
        self.assertEqual(result['filerName'], FILER_NAME)
        self.assertEqual(result['docID'], DOC_ID)
        self.assertEqual(result['issuedDate'], "2023-06-22")

    def test_xbrl_parser_without_yahoo_data(self):
        """Test that XBRL parser works correctly without Yahoo Finance data"""
        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=None
        )

        # Verify that result is still valid
        self.assertIsNotNone(result)

        # Yahoo-specific fields should be None
        self.assertIsNone(result['stockPrice'])
        self.assertIsNone(result['characteristic'])
        self.assertIsNone(result['employees'])
        self.assertIsNone(result['netSales'])
        self.assertIsNone(result['operatingIncome'])
        self.assertIsNone(result['ordinaryIncome'])

        # XBRL data should still be present
        self.assertEqual(result['equity'], EQUITY)
        self.assertEqual(result['cash'], CASH)

    def test_xbrl_parser_with_partial_yahoo_data(self):
        """Test XBRL parser with partial Yahoo Finance data"""
        partial_yahoo_data = {
            'stockPrice': STOCK_PRICE,
            'characteristic': 'テスト企業の事業概要',
            'employees': None,  # Missing data
            'netSales': 8000000000,
            'operatingIncome': None,  # Missing data
        }

        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=partial_yahoo_data
        )

        # Market data (stockPrice) is still used from the fetcher.
        self.assertEqual(result['stockPrice'], STOCK_PRICE)

        # Financial-statement fields come from XBRL (absent here) regardless of
        # what Yahoo provided, so they are None even though Yahoo had netSales.
        self.assertIsNone(result['characteristic'])
        self.assertIsNone(result['netSales'])
        self.assertIsNone(result['employees'])
        self.assertIsNone(result['operatingIncome'])

    def test_calculated_metrics_with_yahoo_data(self):
        """Test that calculated metrics work correctly with Yahoo Finance data"""
        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=self.yahoo_data
        )

        # The derived metrics depend on XBRL-sourced inputs (outstandingShares,
        # eps, bps, netSales, operatingIncome). This fixture's XBRL omits them, so
        # the metrics are None - never fabricated from Yahoo (issue #183).
        self.assertIsNone(result['marketCapitalization'])
        self.assertIsNone(result['per'])
        self.assertIsNone(result['pbr'])
        self.assertIsNone(result['operatingIncomeRate'])
        self.assertIsNone(result['ordinaryIncomeRate'])

    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    @patch('lib.data_scraper.sync_playwright')
    def test_end_to_end_integration(self, mock_playwright, mock_generate_urls, mock_get_ticker):
        """Test end-to-end integration from Yahoo Finance scraping to XBRL parsing"""
        # Setup mocks
        mock_get_ticker.return_value = "9999.T"
        mock_generate_urls.return_value = {
            'profile': 'https://finance.yahoo.co.jp/quote/9999.T/profile',
            'performance': 'https://finance.yahoo.co.jp/quote/9999.T/performance',
            'financials': 'https://finance.yahoo.co.jp/quote/9999.T/financials'
        }

        # Mock Playwright and page interactions
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_p = Mock()

        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Mock extraction functions to return test data
        with patch('lib.data_scraper.extract_profile_data') as mock_extract_profile:
            with patch('lib.data_scraper.extract_performance_data') as mock_extract_performance:
                with patch('lib.data_scraper.extract_financial_data') as mock_extract_financial:

                    # Configure mocks to populate data
                    def populate_profile(page, data):
                        data.update({
                            'stockPrice': STOCK_PRICE,
                            'characteristic': 'テスト企業の事業概要',
                            'employees': 1000
                        })

                    def populate_performance(page, period, data):
                        data.update({
                            'netSales': 8000000000,
                            'operatingIncome': 900000000,
                            'ordinaryIncome': 850000000,
                            'netIncome': 600000000
                        })

                    def populate_financial(page, period, data):
                        data.update({
                            'eps': 60.0,
                            'bps': 500.0,
                            'depreciation': 300000000,
                            'outstandingShares': 10000000,
                            'debt': 2000000000
                        })

                    mock_extract_profile.side_effect = populate_profile
                    mock_extract_performance.side_effect = populate_performance
                    mock_extract_financial.side_effect = populate_financial

                    # Get Yahoo Finance data
                    yahoo_result = get_financial_data(SEC_CODE, "2023年3月期")

                    # Parse XBRL with Yahoo data
                    final_result = self.xbrl_parser.parse_financial_data(
                        self.xbrl_content,
                        sec_code=SEC_CODE,
                        filer_name=FILER_NAME,
                        doc_id=DOC_ID,
                        period_end="2023-03-31",
                        issued_date="2023-06-22",
                        yahoo_data=yahoo_result
                    )

                    # Verify complete integration
                    self.assertIsNotNone(final_result)
                    self.assertEqual(final_result['stockPrice'], STOCK_PRICE)
                    self.assertEqual(final_result['equity'], EQUITY)
                    # marketCap and per depend on XBRL-sourced shares/eps, absent
                    # in this fixture, so they are None (issue #183).
                    self.assertIsNone(final_result['marketCapitalization'])
                    self.assertIsNone(final_result['per'])

    def test_yahoo_data_field_mapping(self):
        """Only market-data fields map from the fetcher; financial-statement
        fields are sourced from XBRL (issue #183)."""
        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=self.yahoo_data
        )

        # Only stockPrice still comes from the fetcher.
        self.assertIn('stockPrice', result)
        self.assertEqual(result['stockPrice'], self.yahoo_data['stockPrice'])

        # Financial-statement fields come from XBRL (absent here -> None), never
        # from the fetcher. As of issue #184 this includes ordinaryIncome and debt.
        for field in ['characteristic', 'employees', 'netSales', 'operatingIncome',
                      'ordinaryIncome', 'netIncome', 'eps', 'bps', 'depreciation',
                      'outstandingShares', 'debt']:
            self.assertIn(field, result)
            self.assertIsNone(result[field])

    def test_error_handling_in_integration(self):
        """Test error handling when Yahoo Finance data has issues"""
        # Create Yahoo data with invalid values
        invalid_yahoo_data = {
            'stockPrice': "invalid",  # Should be numeric
            'employees': -1,  # Negative value
            'netSales': None,
            'eps': 0,  # Zero EPS
        }

        # Parser should handle gracefully
        result = self.xbrl_parser.parse_financial_data(
            self.xbrl_content,
            sec_code=SEC_CODE,
            filer_name=FILER_NAME,
            doc_id=DOC_ID,
            period_end="2023-03-31",
            issued_date="2023-06-22",
            yahoo_data=invalid_yahoo_data
        )

        # Result should still be valid
        self.assertIsNotNone(result)

        # Calculated metrics should handle invalid data gracefully
        # (PER calculation with zero EPS should result in None or handle appropriately)
        if 'per' in result:
            self.assertTrue(result['per'] is None or result['per'] == 0)


if __name__ == '__main__':
    unittest.main()
