#!/usr/bin/env python3
"""
Test cases for stock exchange mapping functionality
"""

import unittest
import sys
import os
from unittest.mock import patch, mock_open

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.edinet_common import get_stock_exchange_code
import lib.edinet_common as edinet_common


class TestStockExchangeMapping(unittest.TestCase):
    """Test cases for get_stock_exchange_code function"""
    
    def setUp(self):
        """Set up test cases"""
        # Clear cache before each test
        edinet_common._stock_exchange_mapping_cache = None
    
    def test_nagoya_stock_exchange(self):
        """Test Nagoya Stock Exchange (N) mappings"""
        nagoya_codes = [
            "1738", "1777", "1869", "1892", "2467", "2551", "259A", "2902",
            "3032", "3066", "3260", "3346", "3384", "3419", "3442", "3504",
            "3739", "3775", "3808", "3830", "3952", "4349", "5075", "5241",
            "5342", "5343", "5530", "5607", "5836", "5979", "5993", "6025",
            "6111", "6142", "6225", "6439", "6623", "6655", "6846", "7076",
            "7227", "7485", "7488", "7675", "7790", "7870", "7950", "8071",
            "8145", "8190", "8228", "9040", "9170", "9357", "9359", "9402",
            "9471", "9643", "9664"
        ]
        
        for code in nagoya_codes:
            with self.subTest(code=code):
                self.assertEqual(get_stock_exchange_code(code), "N", 
                                f"Code {code} should map to Nagoya (N)")
    
    def test_fukuoka_stock_exchange(self):
        """Test Fukuoka Stock Exchange (F) mappings"""
        fukuoka_codes = [
            "1771", "1999", "2058", "231A", "242A", "2919", "2974", "3047",
            "3824", "4018", "4250", "4827", "4995", "5953", "6076", "7441",
            "7533", "7894", "8398", "8554", "8559", "8560", "9035", "9388",
            "9407", "9942"
        ]
        
        for code in fukuoka_codes:
            with self.subTest(code=code):
                self.assertEqual(get_stock_exchange_code(code), "F",
                                f"Code {code} should map to Fukuoka (F)")
    
    def test_sapporo_stock_exchange(self):
        """Test Sapporo Stock Exchange (S) mappings"""
        sapporo_codes = [
            "1449", "1832", "2137", "2172", "2218", "2928", "2976", "3055",
            "3136", "3849", "3977", "4834", "5039", "5579", "7118", "8594",
            "9027", "9085"
        ]
        
        for code in sapporo_codes:
            with self.subTest(code=code):
                self.assertEqual(get_stock_exchange_code(code), "S",
                                f"Code {code} should map to Sapporo (S)")
    
    def test_tokyo_stock_exchange_default(self):
        """Test Tokyo Stock Exchange (T) as default for unmapped codes"""
        tokyo_codes = [
            "7203",  # Toyota
            "9984",  # SoftBank
            "4755",  # Rakuten
            "6758",  # Sony
            "9983",  # Fast Retailing
            "8306",  # Mitsubishi UFJ
            "1234",  # Random unmapped code
            "9999",  # Another unmapped code
        ]
        
        for code in tokyo_codes:
            with self.subTest(code=code):
                self.assertEqual(get_stock_exchange_code(code), "T",
                                f"Code {code} should default to Tokyo (T)")
    
    def test_cache_functionality(self):
        """Test that the mapping is cached after first load"""
        # First call loads the file
        result1 = get_stock_exchange_code("1738")
        self.assertEqual(result1, "N")
        
        # Cache should be populated
        self.assertIsNotNone(edinet_common._stock_exchange_mapping_cache)
        
        # Mock the open function to ensure file is not read again
        with patch("builtins.open", mock_open()) as mock_file:
            result2 = get_stock_exchange_code("2919")
            self.assertEqual(result2, "F")
            # File should not be opened again due to caching
            mock_file.assert_not_called()
    
    def test_missing_config_file(self):
        """Test behavior when config file is missing"""
        # Clear cache to force reload
        edinet_common._stock_exchange_mapping_cache = None
        
        # Mock file opening to raise FileNotFoundError
        with patch("builtins.open", side_effect=FileNotFoundError("Config file not found")):
            # Should default to Tokyo (T) when file is missing
            result = get_stock_exchange_code("1738")
            self.assertEqual(result, "T", 
                           "Should default to Tokyo (T) when config file is missing")
    
    def test_invalid_yaml_format(self):
        """Test behavior when YAML file has invalid format"""
        # Clear cache to force reload
        edinet_common._stock_exchange_mapping_cache = None
        
        invalid_yaml = "invalid: yaml: content:"
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("yaml.safe_load", side_effect=Exception("Invalid YAML")):
                # Should default to Tokyo (T) when YAML is invalid
                result = get_stock_exchange_code("1738")
                self.assertEqual(result, "T",
                               "Should default to Tokyo (T) when YAML is invalid")
    
    def test_empty_mapping(self):
        """Test behavior when mapping is empty"""
        # Clear cache to force reload
        edinet_common._stock_exchange_mapping_cache = None
        
        empty_yaml = "stock_exchanges: {}"
        
        with patch("builtins.open", mock_open(read_data=empty_yaml)):
            # All codes should default to Tokyo (T)
            result = get_stock_exchange_code("1738")
            self.assertEqual(result, "T",
                           "Should default to Tokyo (T) when mapping is empty")
    
    def test_edge_cases(self):
        """Test edge cases for security codes"""
        test_cases = [
            ("", "T"),           # Empty string
            ("123", "T"),        # 3-digit code
            ("12345", "T"),      # 5-digit code
            ("ABCD", "T"),       # Non-numeric code
            ("0000", "T"),       # All zeros
            (None, "T"),         # None value (if handled)
        ]
        
        for code, expected in test_cases:
            with self.subTest(code=code):
                try:
                    result = get_stock_exchange_code(code)
                    self.assertEqual(result, expected,
                                   f"Code '{code}' should default to Tokyo (T)")
                except TypeError:
                    # None might raise TypeError, which is acceptable
                    if code is None:
                        pass
                    else:
                        raise


class TestYahooURLGeneration(unittest.TestCase):
    """Test Yahoo Finance URL generation with stock exchange codes"""
    
    def test_url_format(self):
        """Test that URLs are generated in correct format"""
        test_cases = [
            ("1738", "https://finance.yahoo.co.jp/quote/1738.N"),  # Nagoya
            ("2919", "https://finance.yahoo.co.jp/quote/2919.F"),  # Fukuoka
            ("1449", "https://finance.yahoo.co.jp/quote/1449.S"),  # Sapporo
            ("7203", "https://finance.yahoo.co.jp/quote/7203.T"),  # Tokyo
        ]
        
        for sec_code, expected_url in test_cases:
            with self.subTest(sec_code=sec_code):
                exchange_code = get_stock_exchange_code(sec_code)
                actual_url = f"https://finance.yahoo.co.jp/quote/{sec_code}.{exchange_code}"
                self.assertEqual(actual_url, expected_url,
                               f"URL for {sec_code} should be {expected_url}")


if __name__ == '__main__':
    unittest.main()