import unittest
from unittest.mock import Mock, patch, MagicMock, call
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.data_scraper import (
    extract_preloaded_state,
    parse_numeric_value,
    convert_million_to_yen,
    convert_thousand_to_shares,
    extract_profile_data,
    extract_performance_data,
    extract_financial_data,
    get_financial_data
)


class TestDataScraperUtilities(unittest.TestCase):
    """Test utility functions in data_scraper module"""
    
    def test_parse_numeric_value(self):
        """Test parse_numeric_value function"""
        test_cases = [
            ("1,234,567円", "1234567"),
            ("100人", "100"),
            ("5,000株", "5000"),
            ("123", "123"),
            ("  456  ", "456"),
            (789, "789"),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = parse_numeric_value(input_val)
                self.assertEqual(result, expected)
    
    def test_convert_million_to_yen(self):
        """Test convert_million_to_yen function"""
        test_cases = [
            ("51121", 51121000000),
            ("-1000", -1000000000),
            ("0", 0),
            ("---", None),
            ("N/A", None),
            ("", None),
            ("abc", None),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = convert_million_to_yen(input_val)
                self.assertEqual(result, expected)
    
    def test_convert_thousand_to_shares(self):
        """Test convert_thousand_to_shares function"""
        test_cases = [
            ("58162", 58162000),
            ("1000", 1000000),
            ("0", 0),
            ("---", None),
            ("N/A", None),
            ("", None),
            ("xyz", None),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = convert_thousand_to_shares(input_val)
                self.assertEqual(result, expected)


class TestDataScraperExtraction(unittest.TestCase):
    """Test data extraction functions"""
    
    def setUp(self):
        """Set up mock page object"""
        self.mock_page = Mock()
        
    def test_extract_preloaded_state_from_window(self):
        """Test extracting PRELOADED_STATE from window object"""
        # Mock successful extraction from window
        mock_state = {"test": "data"}
        self.mock_page.evaluate.return_value = mock_state
        self.mock_page.content.return_value = "<html></html>"
        
        result = extract_preloaded_state(self.mock_page)
        self.assertEqual(result, mock_state)
        self.mock_page.evaluate.assert_called_once()
    
    def test_extract_preloaded_state_fallback_regex(self):
        """Test extracting PRELOADED_STATE using regex fallback"""
        # Mock failed window extraction
        self.mock_page.evaluate.side_effect = Exception("Failed")
        
        # Mock HTML content with PRELOADED_STATE
        html_content = """
        <script>
        window.__PRELOADED_STATE__ = {"fallback": "data", "test": 123};
        window.nextFunction();
        </script>
        """
        self.mock_page.content.return_value = html_content
        
        result = extract_preloaded_state(self.mock_page)
        self.assertEqual(result, {"fallback": "data", "test": 123})
    
    def test_extract_preloaded_state_no_data(self):
        """Test when no PRELOADED_STATE is found"""
        self.mock_page.evaluate.return_value = None
        self.mock_page.content.return_value = "<html>No state here</html>"
        
        result = extract_preloaded_state(self.mock_page)
        self.assertEqual(result, {})
    
    def test_extract_profile_data(self):
        """Test extracting profile data from page"""
        financial_data = {}
        
        # Mock PRELOADED_STATE with profile data
        mock_state = {
            "mainStocksPriceBoard": {
                "priceBoard": {
                    "price": "1,234.5"
                }
            },
            "mainStocksProfile": {
                "items": [
                    {
                        "head": "特色",
                        "details": [{"text": "自動車メーカー大手"}]
                    },
                    {
                        "head": "従業員数（連結）",
                        "details": [{"text": "366,283人（23.3）"}]
                    }
                ]
            }
        }
        
        with patch('lib.data_scraper.extract_preloaded_state', return_value=mock_state):
            extract_profile_data(self.mock_page, financial_data)
        
        self.assertEqual(financial_data['stockPrice'], 1234.5)
        self.assertEqual(financial_data['characteristic'], "自動車メーカー大手")
        self.assertEqual(financial_data['employees'], 366283)
    
    def test_extract_performance_data(self):
        """Test extracting performance data from page"""
        financial_data = {}
        period_end = "2023年3月期"
        
        # Mock PRELOADED_STATE with performance data
        mock_state = {
            "mainStocksPerformance": {
                "items": [
                    {
                        "period": "2023年3月期",
                        "sales": "37154",
                        "operatingIncome": "2725",
                        "ordinaryIncome": "3932",
                        "netIncome": "2451"
                    }
                ]
            }
        }
        
        # Mock page selectors for fallback
        self.mock_page.query_selector_all.return_value = []
        
        with patch('lib.data_scraper.extract_preloaded_state', return_value=mock_state):
            extract_performance_data(self.mock_page, period_end, financial_data)
        
        self.assertEqual(financial_data['netSales'], 37154000000)
        self.assertEqual(financial_data['operatingIncome'], 2725000000)
        self.assertEqual(financial_data['ordinaryIncome'], 3932000000)
        self.assertEqual(financial_data['netIncome'], 2451000000)
    
    def test_extract_financial_data(self):
        """Test extracting financial data from page"""
        financial_data = {}
        period_end = "2023年3月期"
        
        # Mock table structure
        mock_table = Mock()
        mock_rows = []
        
        # Create mock header row
        mock_header_row = Mock()
        mock_header_cells = []
        header_data = [
            "決算期",          # Period
            "EPS",           # EPS
            "BPS",           # BPS
            "ROE",           # Empty
            "ROA",           # Empty
            "自己資本比率",    # Empty
            "配当性向",       # Empty
            "配当利回り",     # Empty
            "有利子負債",     # Debt
            "減価償却",       # Depreciation
            "発行済株式数"    # Outstanding shares
        ]
        
        for data in header_data:
            cell = Mock()
            cell.text_content.return_value = data
            mock_header_cells.append(cell)
        
        def header_row_selector(selector):
            if selector == 'th, td':
                return mock_header_cells
            return []
        
        mock_header_row.query_selector_all = header_row_selector
        mock_rows.append(mock_header_row)
        
        # Create mock data row
        mock_data_row = Mock()
        mock_data_cells = []
        
        # Mock cells with text content
        cell_data = [
            "2023年3月期",  # Period
            "123.45",       # EPS
            "2345.67",      # BPS
            "---",          # Empty
            "---",          # Empty
            "---",          # Empty
            "---",          # Empty
            "---",          # Empty
            "15000",        # Debt
            "3500",         # Depreciation
            "432100"        # Outstanding shares
        ]
        
        for data in cell_data:
            cell = Mock()
            cell.text_content.return_value = data
            mock_data_cells.append(cell)
        
        def data_row_selector(selector):
            if selector == 'td, th':
                return mock_data_cells
            return []
        
        mock_data_row.query_selector_all = data_row_selector
        mock_rows.append(mock_data_row)
        
        mock_table.query_selector_all.return_value = mock_rows
        self.mock_page.query_selector_all.return_value = [mock_table]
        
        extract_financial_data(self.mock_page, period_end, financial_data)
        
        self.assertEqual(financial_data['eps'], 123.45)
        self.assertEqual(financial_data['bps'], 2345.67)
        self.assertEqual(financial_data['debt'], 15000000000)
        self.assertEqual(financial_data['depreciation'], 3500000000)
        self.assertEqual(financial_data['outstandingShares'], 432100000)


class TestGetFinancialData(unittest.TestCase):
    """Test the main get_financial_data function"""
    
    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    @patch('lib.data_scraper.sync_playwright')
    def test_get_financial_data_success(self, mock_playwright, mock_generate_urls, mock_get_ticker):
        """Test successful financial data retrieval"""
        # Setup mocks
        mock_get_ticker.return_value = "7203.T"
        mock_generate_urls.return_value = {
            'profile': 'https://finance.yahoo.co.jp/quote/7203.T/profile',
            'performance': 'https://finance.yahoo.co.jp/quote/7203.T/performance?styl=performance',
            'financials': 'https://finance.yahoo.co.jp/quote/7203.T/performance?styl=financials'
        }
        
        # Mock Playwright context
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_chromium = Mock()
        mock_p = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock page navigation
        mock_page.goto.return_value = None
        
        # Mock extraction functions
        with patch('lib.data_scraper.extract_profile_data') as mock_extract_profile:
            with patch('lib.data_scraper.extract_performance_data') as mock_extract_performance:
                with patch('lib.data_scraper.extract_financial_data') as mock_extract_financial:
                    
                    # Call the function
                    result = get_financial_data("7203", "2023年3月期")
                    
                    # Verify mocks were called
                    mock_get_ticker.assert_called_once_with("7203")
                    mock_generate_urls.assert_called_once_with("7203.T")
                    
                    # Verify page navigations
                    self.assertEqual(mock_page.goto.call_count, 3)
                    
                    # Verify extraction functions were called
                    mock_extract_profile.assert_called_once()
                    mock_extract_performance.assert_called_once()
                    mock_extract_financial.assert_called_once()
                    
                    # Verify context manager was properly used
                    mock_playwright.return_value.__enter__.assert_called_once()
                    mock_playwright.return_value.__exit__.assert_called_once()
                    
                    # Check that all expected fields are in result
                    expected_fields = [
                        'stockPrice', 'characteristic', 'employees', 'netSales',
                        'operatingIncome', 'ordinaryIncome', 'netIncome', 'eps', 'bps',
                        'depreciation', 'outstandingShares', 'debt'
                    ]
                    for field in expected_fields:
                        self.assertIn(field, result)
    
    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    @patch('lib.data_scraper.sync_playwright')
    def test_get_financial_data_with_error(self, mock_playwright, mock_generate_urls, mock_get_ticker):
        """Test error handling in get_financial_data"""
        # Setup mocks
        mock_get_ticker.return_value = "7203.T"
        mock_generate_urls.return_value = {
            'profile': 'https://finance.yahoo.co.jp/quote/7203.T/profile',
            'performance': 'https://finance.yahoo.co.jp/quote/7203.T/performance',
            'financials': 'https://finance.yahoo.co.jp/quote/7203.T/financials'
        }
        
        # Mock Playwright to raise an error
        mock_playwright.side_effect = Exception("Network error")
        
        # Call should raise the exception
        with self.assertRaises(Exception) as context:
            get_financial_data("7203", "2023年3月期")
        
        self.assertIn("Network error", str(context.exception))
    
    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    @patch('lib.data_scraper.sync_playwright')
    def test_get_financial_data_browser_context(self, mock_playwright, mock_generate_urls, mock_get_ticker):
        """Test that browser context is set up correctly"""
        # Setup mocks
        mock_get_ticker.return_value = "7203.T"
        mock_generate_urls.return_value = {
            'profile': 'url1',
            'performance': 'url2',
            'financials': 'url3'
        }
        
        # Mock Playwright context
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_chromium = Mock()
        mock_p = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock extraction functions
        with patch('lib.data_scraper.extract_profile_data'):
            with patch('lib.data_scraper.extract_performance_data'):
                with patch('lib.data_scraper.extract_financial_data'):
                    
                    # Call the function
                    get_financial_data("7203", "2023年3月期")
                    
                    # Verify browser was launched in headless mode
                    mock_p.chromium.launch.assert_called_once_with(headless=True)
                    
                    # Verify context was created with user agent
                    mock_browser.new_context.assert_called_once()
                    call_args = mock_browser.new_context.call_args
                    self.assertIn('user_agent', call_args[1])
                    self.assertIn('Mozilla', call_args[1]['user_agent'])


if __name__ == '__main__':
    unittest.main()