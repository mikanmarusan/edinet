import unittest
from unittest.mock import patch, mock_open
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.ticker_generator import get_ticker_from_security_code


class TestTickerGenerator(unittest.TestCase):
    
    def setUp(self):
        # Sample YAML content for mocking
        self.mock_yaml_content = """
stock_exchanges:
  '7203': 'T'
  '9984': 'T'
  '4755': 'T'
  '2413': 'N'
  '3382': 'S'
  '6701': 'F'
"""

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_get_ticker_with_mapped_exchange(self, mock_yaml_load, mock_file):
        """Test ticker generation for security codes with mapped exchanges"""
        # Mock the YAML loading
        mock_yaml_load.return_value = {
            'stock_exchanges': {
                '7203': 'T',
                '9984': 'T',
                '4755': 'T',
                '2413': 'N',
                '3382': 'S',
                '6701': 'F'
            }
        }
        
        # Test various mapped exchanges
        test_cases = [
            ('7203', '7203.T'),  # Tokyo Stock Exchange
            ('9984', '9984.T'),  # Tokyo Stock Exchange
            ('2413', '2413.N'),  # Nagoya Stock Exchange
            ('3382', '3382.S'),  # Sapporo Stock Exchange
            ('6701', '6701.F'),  # Fukuoka Stock Exchange
        ]
        
        for sec_code, expected_ticker in test_cases:
            with self.subTest(sec_code=sec_code):
                result = get_ticker_from_security_code(sec_code)
                self.assertEqual(result, expected_ticker)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_get_ticker_default_to_tokyo(self, mock_yaml_load, mock_file):
        """Test ticker generation defaults to Tokyo Stock Exchange (.T) for unmapped codes"""
        # Mock the YAML loading with limited mappings
        mock_yaml_load.return_value = {
            'stock_exchanges': {
                '7203': 'T',
                '9984': 'T'
            }
        }
        
        # Test unmapped security codes
        unmapped_codes = ['1234', '5678', '9999', '0000']
        
        for sec_code in unmapped_codes:
            with self.subTest(sec_code=sec_code):
                result = get_ticker_from_security_code(sec_code)
                self.assertEqual(result, f"{sec_code}.T")

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_empty_mapping_file(self, mock_yaml_load, mock_file):
        """Test behavior when mapping file has no stock_exchanges section"""
        # Mock empty or missing stock_exchanges section
        mock_yaml_load.return_value = {}
        
        result = get_ticker_from_security_code('7203')
        self.assertEqual(result, '7203.T')
        
        # Test with empty dict instead of None
        mock_yaml_load.return_value = {'stock_exchanges': {}}
        result = get_ticker_from_security_code('7203')
        self.assertEqual(result, '7203.T')

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_file_path_construction(self, mock_yaml_load, mock_file):
        """Test that the correct config file path is constructed"""
        mock_yaml_load.return_value = {'stock_exchanges': {}}
        
        # Call the function
        get_ticker_from_security_code('7203')
        
        # Verify the correct file path was used
        expected_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'lib', '../config/stock_exchange_mapping.yml'
        )
        expected_path = os.path.normpath(expected_path)
        
        # Check that open was called with the correct path
        mock_file.assert_called()
        actual_path = os.path.normpath(mock_file.call_args[0][0])
        self.assertEqual(actual_path, expected_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_various_security_code_formats(self, mock_yaml_load, mock_file):
        """Test ticker generation with various security code formats"""
        mock_yaml_load.return_value = {
            'stock_exchanges': {
                '123': 'N',
                '12345': 'S'
            }
        }
        
        # Test different length security codes
        test_cases = [
            ('123', '123.N'),    # 3-digit code
            ('12345', '12345.S'), # 5-digit code
            ('1', '1.T'),        # 1-digit code (unmapped)
            ('123456', '123456.T') # 6-digit code (unmapped)
        ]
        
        for sec_code, expected_ticker in test_cases:
            with self.subTest(sec_code=sec_code):
                result = get_ticker_from_security_code(sec_code)
                self.assertEqual(result, expected_ticker)


if __name__ == '__main__':
    unittest.main()