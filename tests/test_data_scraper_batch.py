"""
Tests for batch processing functionality in data_scraper module.

Covers Issue #131 requirements:
- Type hints validation
- Edge case handling (empty input, invalid context)
- Batch processing with multiple companies
- Error handling and recovery
- Performance optimization verification
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import os
import sys
from typing import Dict, List, Tuple, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.data_scraper import (
    get_financial_data_with_context,
    get_financial_data_batch,
    get_financial_data
)


class TestBatchProcessing(unittest.TestCase):
    """Test batch processing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_page = Mock()
        self.mock_context.new_page.return_value = self.mock_page
        self.mock_context.pages = []  # Valid context has pages attribute
        
        # Mock page methods
        self.mock_page.set_default_timeout = Mock()
        self.mock_page.goto = Mock()
        self.mock_page.wait_for_selector = Mock()
        self.mock_page.close = Mock()
        
        # Mock successful data extraction
        self.sample_financial_data = {
            'stockPrice': 1500.0,
            'characteristic': 'Test Company',
            'employees': 10000,
            'netSales': 1000000000,
            'operatingIncome': 100000000,
            'ordinaryIncome': 120000000,
            'netIncome': 80000000,
            'eps': 123.45,
            'bps': 1234.56,
            'debt': 500000000,
            'depreciation': 50000000,
            'outstandingShares': 1000000
        }
    
    @patch('lib.data_scraper.extract_profile_data')
    @patch('lib.data_scraper.extract_performance_data')
    @patch('lib.data_scraper.extract_financial_data')
    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    def test_get_financial_data_with_context_success(
        self, mock_urls, mock_ticker, mock_extract_fin,
        mock_extract_perf, mock_extract_prof
    ):
        """Test successful data retrieval with context"""
        # Setup mocks
        mock_ticker.return_value = "7203.T"
        mock_urls.return_value = {
            'profile': 'url1',
            'performance': 'url2', 
            'financials': 'url3'
        }
        
        # Mock extraction functions to populate financial_data
        def populate_profile(page, financial_data):
            financial_data.update({
                'stockPrice': 1500.0,
                'characteristic': 'Auto manufacturer',
                'employees': 366000
            })
        
        def populate_performance(page, period, financial_data):
            financial_data.update({
                'netSales': 37000000000000,
                'operatingIncome': 2700000000000,
                'ordinaryIncome': 3900000000000,
                'netIncome': 2400000000000
            })
        
        def populate_financials(page, period, financial_data):
            financial_data.update({
                'eps': 234.56,
                'bps': 3456.78,
                'debt': 15000000000000,
                'depreciation': 1200000000000,
                'outstandingShares': 3200000000
            })
        
        mock_extract_prof.side_effect = populate_profile
        mock_extract_perf.side_effect = populate_performance
        mock_extract_fin.side_effect = populate_financials
        
        # Test function
        result = get_financial_data_with_context("7203", "2023年3月期", self.mock_context)
        
        # Verify results
        self.assertIsInstance(result, dict)
        self.assertEqual(result['stockPrice'], 1500.0)
        self.assertEqual(result['characteristic'], 'Auto manufacturer')
        self.assertEqual(result['employees'], 366000)
        self.assertEqual(result['netSales'], 37000000000000)
        
        # Verify page was closed
        self.mock_page.close.assert_called_once()
    
    def test_get_financial_data_with_context_invalid_context(self):
        """Test error handling for invalid context"""
        # Test with None context
        with self.assertRaises(ValueError) as cm:
            get_financial_data_with_context("7203", "2023年3月期", None)
        self.assertIn("Browser context cannot be None", str(cm.exception))
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.data_scraper.get_financial_data_with_context')
    def test_batch_processing_multiple_companies_success(
        self, mock_get_with_context, mock_playwright
    ):
        """Test successful batch processing of multiple companies"""
        # Setup playwright mock
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        
        # Mock successful data retrieval for each company
        mock_get_with_context.side_effect = [
            {'stockPrice': 1500.0, 'netSales': 37000000000000},  # Toyota
            {'stockPrice': 8000.0, 'netSales': 9000000000000},   # Softbank
            {'stockPrice': 900.0, 'netSales': 1500000000000}     # Rakuten
        ]
        
        # Test data
        companies = [
            ("7203", "2023年3月期"),
            ("9984", "2023年2月期"),
            ("4755", "2023年12月期")
        ]
        
        # Execute batch processing
        results = get_financial_data_batch(companies)
        
        # Verify results structure
        self.assertEqual(len(results), 3)
        self.assertIn("7203", results)
        self.assertIn("9984", results)
        self.assertIn("4755", results)
        
        # Verify each result
        for sec_code in ["7203", "9984", "4755"]:
            self.assertTrue(results[sec_code]['success'])
            self.assertIn('data', results[sec_code])
            self.assertIn('stockPrice', results[sec_code]['data'])
            self.assertIn('netSales', results[sec_code]['data'])
        
        # Verify browser was closed
        mock_browser.close.assert_called_once()
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.data_scraper.get_financial_data_with_context')
    def test_batch_processing_mixed_success_failure(
        self, mock_get_with_context, mock_playwright
    ):
        """Test batch processing with some successes and some failures"""
        # Setup playwright mock
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        
        # Mock mixed results - success, failure, success
        mock_get_with_context.side_effect = [
            {'stockPrice': 1500.0, 'netSales': 37000000000000},  # Success
            RuntimeError("Network timeout for 9984"),             # Failure
            {'stockPrice': 900.0, 'netSales': 1500000000000}     # Success
        ]
        
        # Test data
        companies = [
            ("7203", "2023年3月期"),
            ("9984", "2023年2月期"),
            ("4755", "2023年12月期")
        ]
        
        # Execute batch processing
        results = get_financial_data_batch(companies)
        
        # Verify results
        self.assertEqual(len(results), 3)
        
        # First company should succeed
        self.assertTrue(results["7203"]['success'])
        self.assertIn('data', results["7203"])
        
        # Second company should fail
        self.assertFalse(results["9984"]['success'])
        self.assertIn('error', results["9984"])
        self.assertIn("Network timeout", results["9984"]['error'])
        
        # Third company should succeed (batch continues after failure)
        self.assertTrue(results["4755"]['success'])
        self.assertIn('data', results["4755"])
    
    def test_batch_processing_empty_input(self):
        """Test batch processing with empty input list"""
        # Should return empty dict without errors
        results = get_financial_data_batch([])
        self.assertEqual(results, {})
    
    
    @patch('lib.data_scraper.sync_playwright')
    def test_batch_processing_browser_initialization_failure(
        self, mock_playwright
    ):
        """Test handling of browser initialization failure"""
        # Mock browser initialization failure
        mock_playwright.side_effect = Exception("Browser failed to launch")
        
        # Test data
        companies = [
            ("7203", "2023年3月期"),
            ("9984", "2023年2月期")
        ]
        
        # Execute batch processing
        results = get_financial_data_batch(companies)
        
        # All companies should have failure status
        self.assertEqual(len(results), 2)
        
        for sec_code in ["7203", "9984"]:
            self.assertFalse(results[sec_code]['success'])
            self.assertIn('error', results[sec_code])
            self.assertIn("Browser initialization failed", results[sec_code]['error'])
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.data_scraper.get_financial_data_with_context')
    def test_batch_processing_single_browser_instance(
        self, mock_get_with_context, mock_playwright
    ):
        """Test that batch processing uses single browser instance for all companies"""
        # Setup playwright mock
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        
        # Mock successful data retrieval
        mock_get_with_context.return_value = self.sample_financial_data
        
        # Test data - multiple companies
        companies = [
            ("7203", "2023年3月期"),
            ("9984", "2023年2月期"),
            ("4755", "2023年12月期"),
            ("6758", "2023年3月期"),
            ("9433", "2023年3月期")
        ]
        
        # Execute batch processing
        results = get_financial_data_batch(companies)
        
        # Verify only one browser instance was created
        mock_p.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()
        
        # Verify get_financial_data_with_context was called with same context
        self.assertEqual(mock_get_with_context.call_count, 5)
        for call_args in mock_get_with_context.call_args_list:
            # Third argument should be the same context
            self.assertEqual(call_args[0][2], mock_context)
        
        # Verify browser was closed once at the end
        mock_browser.close.assert_called_once()
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.data_scraper.logger')
    def test_batch_processing_logging(self, mock_logger, mock_playwright):
        """Test proper logging during batch processing"""
        # Setup playwright mock
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        
        # Test empty input logging
        get_financial_data_batch([])
        mock_logger.info.assert_called_with("No companies provided for batch processing")
        
        # Test processing logging
        with patch('lib.data_scraper.get_financial_data_with_context') as mock_get:
            mock_get.return_value = self.sample_financial_data
            
            companies = [("7203", "2023年3月期")]
            get_financial_data_batch(companies)
            
            # Should log processing for each company
            mock_logger.info.assert_any_call(
                "Processing company 7203 with period 2023年3月期"
            )
    
    def test_type_hints_existence(self):
        """Test that functions have proper type hints"""
        import inspect
        from typing import get_type_hints
        
        # Test get_financial_data_with_context
        hints = get_type_hints(get_financial_data_with_context)
        self.assertIn('secCode', hints)
        self.assertIn('periodEnd', hints)
        self.assertIn('context', hints)
        self.assertIn('return', hints)
        
        # Test get_financial_data_batch
        hints = get_type_hints(get_financial_data_batch)
        self.assertIn('companies_data', hints)
        self.assertIn('return', hints)
        
        # Test get_financial_data
        hints = get_type_hints(get_financial_data)
        self.assertIn('secCode', hints)
        self.assertIn('periodEnd', hints)
        self.assertIn('return', hints)


class TestPerformanceOptimization(unittest.TestCase):
    """Test performance optimization aspects"""
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.data_scraper.get_financial_data_with_context')
    @patch('lib.data_scraper.time')
    def test_batch_processing_performance(
        self, mock_time, mock_get_with_context, mock_playwright
    ):
        """Test that batch processing is more efficient than individual calls"""
        # Setup mocks
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        
        mock_get_with_context.return_value = {'stockPrice': 1000.0}
        
        # Large batch of companies
        companies = [(str(i), f"2023年{i%12+1}月期") for i in range(1000, 1050)]
        
        # Process batch
        results = get_financial_data_batch(companies)
        
        # Verify all succeeded
        self.assertEqual(len(results), 50)
        for sec_code, result in results.items():
            self.assertTrue(result['success'])
        
        # Verify browser was created only once
        mock_p.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()
        mock_browser.close.assert_called_once()
    
    @patch('lib.data_scraper.sync_playwright')
    @patch('lib.ticker_generator.get_ticker_from_security_code')
    @patch('lib.url_generator.generate_yahoo_finance_urls')
    @patch('lib.data_scraper.extract_profile_data')
    @patch('lib.data_scraper.extract_performance_data')
    @patch('lib.data_scraper.extract_financial_data')
    def test_context_reuse_verification(
        self, mock_extract_fin, mock_extract_perf, mock_extract_prof,
        mock_urls, mock_ticker, mock_playwright
    ):
        """Test that browser context is properly reused across multiple calls"""
        # Setup mocks
        mock_p = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.pages = []
        
        mock_ticker.return_value = "TEST.T"
        mock_urls.return_value = {
            'profile': 'url1',
            'performance': 'url2',
            'financials': 'url3'
        }
        
        mock_page.set_default_timeout = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_selector = Mock()
        mock_page.close = Mock()
        
        # Process multiple companies
        companies = [("1000", "2023年3月期"), ("1001", "2023年3月期"), ("1002", "2023年3月期")]
        get_financial_data_batch(companies)
        
        # Context should be created once
        mock_browser.new_context.assert_called_once()
        
        # But new page should be created for each company
        self.assertEqual(mock_context.new_page.call_count, 3)
        
        # And each page should be closed
        self.assertEqual(mock_page.close.call_count, 3)


if __name__ == '__main__':
    unittest.main()