import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.url_generator import generate_yahoo_finance_urls


class TestURLGenerator(unittest.TestCase):
    
    def test_generate_urls_basic(self):
        """Test basic URL generation for a standard ticker"""
        ticker = "7203.T"
        urls = generate_yahoo_finance_urls(ticker)
        
        # Check that all expected keys are present
        expected_keys = ['profile', 'performance', 'financials']
        self.assertEqual(set(urls.keys()), set(expected_keys))
        
        # Check URL structure
        base_url = "https://finance.yahoo.co.jp/quote/"
        self.assertEqual(urls['profile'], f"{base_url}7203.T/profile")
        self.assertEqual(urls['performance'], f"{base_url}7203.T/performance?styl=performance")
        self.assertEqual(urls['financials'], f"{base_url}7203.T/performance?styl=financials")

    def test_generate_urls_different_exchanges(self):
        """Test URL generation for tickers from different exchanges"""
        test_cases = [
            "7203.T",  # Tokyo
            "2413.N",  # Nagoya
            "3382.S",  # Sapporo
            "6701.F",  # Fukuoka
        ]
        
        base_url = "https://finance.yahoo.co.jp/quote/"
        
        for ticker in test_cases:
            with self.subTest(ticker=ticker):
                urls = generate_yahoo_finance_urls(ticker)
                
                # Verify URLs contain the correct ticker
                self.assertIn(ticker, urls['profile'])
                self.assertIn(ticker, urls['performance'])
                self.assertIn(ticker, urls['financials'])
                
                # Verify URL structure
                self.assertEqual(urls['profile'], f"{base_url}{ticker}/profile")
                self.assertEqual(urls['performance'], f"{base_url}{ticker}/performance?styl=performance")
                self.assertEqual(urls['financials'], f"{base_url}{ticker}/performance?styl=financials")

    def test_generate_urls_special_characters(self):
        """Test URL generation with various ticker formats"""
        # Test with numbers only, dots, and other variations
        test_cases = [
            "1234",      # No exchange suffix
            "1234.T",    # Standard format
            "12345.T",   # 5-digit code
            "123.T",     # 3-digit code
            "1.T",       # Single digit
        ]
        
        for ticker in test_cases:
            with self.subTest(ticker=ticker):
                urls = generate_yahoo_finance_urls(ticker)
                
                # Should always return a dictionary with 3 keys
                self.assertEqual(len(urls), 3)
                self.assertIn('profile', urls)
                self.assertIn('performance', urls)
                self.assertIn('financials', urls)
                
                # URLs should contain the ticker as-is
                for url in urls.values():
                    self.assertIn(ticker, url)

    def test_url_format_consistency(self):
        """Test that URLs maintain consistent format"""
        ticker = "9984.T"
        urls = generate_yahoo_finance_urls(ticker)
        
        # All URLs should start with HTTPS
        for url in urls.values():
            self.assertTrue(url.startswith("https://"))
        
        # Check for consistent domain
        for url in urls.values():
            self.assertIn("finance.yahoo.co.jp", url)
        
        # Performance and financials should have query parameters
        self.assertIn("?styl=performance", urls['performance'])
        self.assertIn("?styl=financials", urls['financials'])
        
        # Profile should not have query parameters
        self.assertNotIn("?", urls['profile'])

    def test_return_type(self):
        """Test that the function returns the correct type"""
        ticker = "7203.T"
        result = generate_yahoo_finance_urls(ticker)
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # All values should be strings
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    def test_empty_ticker(self):
        """Test behavior with empty ticker"""
        ticker = ""
        urls = generate_yahoo_finance_urls(ticker)
        
        # Should still return valid structure
        self.assertEqual(len(urls), 3)
        
        # URLs should be formed even with empty ticker
        base_url = "https://finance.yahoo.co.jp/quote/"
        self.assertEqual(urls['profile'], f"{base_url}/profile")
        self.assertEqual(urls['performance'], f"{base_url}/performance?styl=performance")
        self.assertEqual(urls['financials'], f"{base_url}/performance?styl=financials")

    def test_unicode_handling(self):
        """Test URL generation with unicode characters"""
        # While tickers are typically alphanumeric, test unicode handling
        ticker = "1234.東"
        urls = generate_yahoo_finance_urls(ticker)
        
        # Should handle unicode without errors
        self.assertEqual(len(urls), 3)
        for url in urls.values():
            self.assertIsInstance(url, str)
            self.assertIn(ticker, url)


if __name__ == '__main__':
    unittest.main()