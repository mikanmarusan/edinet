#!/usr/bin/env python3
"""
Tests for issuedDate functionality in XBRL parsing

This test suite verifies that the issuedDate field is correctly:
1. Included in JSON output
2. Positioned correctly (after cash, before retrievedDate)
3. Passed through the parser methods unchanged
4. Handled correctly in edge cases
"""

import unittest
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from lib.xbrl_parser import XBRLParser, FinancialDataExtractor, MetricsCalculator


class TestIssuedDateFunctionality(unittest.TestCase):
    """Test suite for issuedDate field implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = XBRLParser()
        self.test_date = "2025-07-18"
        self.test_sec_code = "1234"
        self.test_filer_name = "Test Company"
        self.test_doc_id = "S1234567"
        self.test_period_end = "2025-03-31"
        
        # Sample XBRL content for testing
        self.sample_xbrl = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
                    xmlns:jpdei_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor">
            <jpdei_cor:CompanyNameInJapaneseDEI>テスト会社</jpdei_cor:CompanyNameInJapaneseDEI>
        </xbrli:xbrl>""".encode('utf-8')
    
    def test_build_financial_data_structure_includes_issued_date(self):
        """Test that _build_financial_data_structure includes issuedDate field"""
        root = ET.fromstring(self.sample_xbrl)
        
        # Mock the extractor methods to return simple values
        with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_cash', return_value=500000):
            
            result = self.parser._build_financial_data_structure(
                root, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, self.test_date
            )
            
            # Verify issuedDate is included
            self.assertIn("issuedDate", result)
            self.assertEqual(result["issuedDate"], self.test_date)
    
    def test_issued_date_field_position(self):
        """Test that issuedDate appears after cash and before retrievedDate"""
        root = ET.fromstring(self.sample_xbrl)
        
        with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_cash', return_value=500000):
            
            result = self.parser._build_financial_data_structure(
                root, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, self.test_date
            )
            
            # Get the keys as a list to check order
            keys = list(result.keys())
            
            # Find positions of the fields
            cash_index = keys.index("cash")
            issued_date_index = keys.index("issuedDate")
            retrieved_date_index = keys.index("retrievedDate")
            
            # Verify ordering
            self.assertLess(cash_index, issued_date_index,
                          "issuedDate should appear after cash")
            self.assertLess(issued_date_index, retrieved_date_index,
                          "issuedDate should appear before retrievedDate")
    
    def test_parse_financial_data_passes_issued_date(self):
        """Test that parse_financial_data correctly passes issued_date parameter"""
        # Create a mock ZIP content containing our sample XBRL
        mock_zip_content = self._create_mock_zip_content()
        
        with patch.object(self.parser.extractor, 'extract_files',
                         return_value={'test.xbrl': self.sample_xbrl}), \
             patch.object(self.parser.extractor, 'find_main_xbrl',
                         return_value=self.sample_xbrl), \
             patch.object(self.parser.calculator, 'calculate_derived_metrics',
                         side_effect=lambda x: x):
            
            result = self.parser.parse_financial_data(
                mock_zip_content, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, self.test_date
            )
            
            self.assertIsNotNone(result)
            self.assertEqual(result["issuedDate"], self.test_date)
    
    def test_issued_date_preserves_format(self):
        """Test that issued_date is preserved as-is without transformation"""
        root = ET.fromstring(self.sample_xbrl)
        test_dates = [
            "2025-07-18",
            "2025-01-01",
            "2025-12-31",
            "2024-02-29",  # Leap year
        ]
        
        for test_date in test_dates:
            with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
                 patch.object(self.parser, '_extract_stock_price', return_value=1000), \
                 patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
                 patch.object(self.parser, '_extract_net_income', return_value=100000), \
                 patch.object(self.parser, '_extract_cash', return_value=500000):
                
                result = self.parser._build_financial_data_structure(
                    root, self.test_sec_code, self.test_filer_name,
                    self.test_doc_id, self.test_period_end, test_date
                )
                
                self.assertEqual(result["issuedDate"], test_date,
                              f"Date {test_date} should be preserved as-is")
    
    def test_retrieved_date_is_current(self):
        """Test that retrievedDate is set to current date while issuedDate is preserved"""
        root = ET.fromstring(self.sample_xbrl)
        past_issued_date = "2024-01-15"
        
        with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_cash', return_value=500000):
            
            result = self.parser._build_financial_data_structure(
                root, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, past_issued_date
            )
            
            # issuedDate should be the past date
            self.assertEqual(result["issuedDate"], past_issued_date)
            
            # retrievedDate should be today
            today = datetime.now().strftime("%Y-%m-%d")
            self.assertEqual(result["retrievedDate"], today)
    
    def test_json_serialization_with_issued_date(self):
        """Test that the complete financial data with issuedDate can be serialized to JSON"""
        root = ET.fromstring(self.sample_xbrl)
        
        with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_cash', return_value=500000), \
             patch.object(self.parser, '_extract_employees', return_value=100), \
             patch.object(self.parser, '_extract_operating_income', return_value=150000), \
             patch.object(self.parser, '_extract_depreciation', return_value=20000), \
             patch.object(self.parser, '_extract_market_cap', return_value=1000000000), \
             patch.object(self.parser, '_extract_per', return_value=10), \
             patch.object(self.parser, '_extract_pbr', return_value=0.5), \
             patch.object(self.parser, '_extract_bps', return_value=2000), \
             patch.object(self.parser, '_extract_equity', return_value=2000000), \
             patch.object(self.parser, '_extract_debt', return_value=1000000), \
             patch.object(self.parser, '_extract_outstanding_shares', return_value=1000000), \
             patch.object(self.parser, '_extract_eps', return_value=100):
            
            result = self.parser._build_financial_data_structure(
                root, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, self.test_date
            )
            
            # The result should already have all the fields from _build_financial_data_structure
            # No need to add calculated metrics here as we're testing the structure itself
            
            # Ensure JSON serialization works
            json_str = json.dumps(result, ensure_ascii=False)
            parsed = json.loads(json_str)
            
            self.assertEqual(parsed["issuedDate"], self.test_date)
            self.assertIn("retrievedDate", parsed)
    
    def test_edge_case_empty_string_issued_date(self):
        """Test behavior with empty string as issued_date"""
        root = ET.fromstring(self.sample_xbrl)
        
        with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_cash', return_value=500000):
            
            result = self.parser._build_financial_data_structure(
                root, self.test_sec_code, self.test_filer_name,
                self.test_doc_id, self.test_period_end, ""
            )
            
            # Empty string should be preserved
            self.assertEqual(result["issuedDate"], "")
    
    def test_edge_case_invalid_date_format(self):
        """Test that invalid date formats are still preserved in issuedDate"""
        root = ET.fromstring(self.sample_xbrl)
        invalid_dates = [
            "2025/07/18",  # Wrong separator
            "18-07-2025",  # Wrong order
            "2025-13-01",  # Invalid month
            "not-a-date",  # Completely invalid
        ]
        
        for invalid_date in invalid_dates:
            with patch.object(self.parser, '_extract_characteristic', return_value="テスト事業"), \
                 patch.object(self.parser, '_extract_stock_price', return_value=1000), \
                 patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
                 patch.object(self.parser, '_extract_net_income', return_value=100000), \
                 patch.object(self.parser, '_extract_cash', return_value=500000):
                
                result = self.parser._build_financial_data_structure(
                    root, self.test_sec_code, self.test_filer_name,
                    self.test_doc_id, self.test_period_end, invalid_date
                )
                
                # Invalid dates should still be preserved as-is
                self.assertEqual(result["issuedDate"], invalid_date,
                              f"Invalid date {invalid_date} should be preserved")
    
    def _create_mock_zip_content(self):
        """Helper method to create mock ZIP content"""
        # For this test, we don't need actual ZIP content
        # since we're mocking the extractor methods
        return b"mock_zip_content"


class TestIntegrationWithFetchScript(unittest.TestCase):
    """Integration tests simulating the full flow from fetch script"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_date = "2025-07-18"
        self.parser = XBRLParser()
    
    def test_issued_date_parameter_flow(self):
        """Test that issued_date parameter flows correctly through the parsing chain"""
        # Create a simple XBRL content
        sample_xbrl = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">
        </xbrli:xbrl>""".encode('utf-8')
        
        # Mock the internal methods to avoid complex XBRL parsing
        with patch.object(self.parser.extractor, 'extract_files',
                         return_value={'test.xbrl': sample_xbrl}), \
             patch.object(self.parser.extractor, 'find_main_xbrl',
                         return_value=sample_xbrl), \
             patch.object(self.parser.calculator, 'calculate_derived_metrics',
                         side_effect=lambda x: x), \
             patch.object(self.parser, '_extract_characteristic', return_value="Test"), \
             patch.object(self.parser, '_extract_stock_price', return_value=1000), \
             patch.object(self.parser, '_extract_net_sales', return_value=1000000), \
             patch.object(self.parser, '_extract_employees', return_value=100), \
             patch.object(self.parser, '_extract_operating_income', return_value=150000), \
             patch.object(self.parser, '_extract_depreciation', return_value=20000), \
             patch.object(self.parser, '_extract_market_cap', return_value=1000000000), \
             patch.object(self.parser, '_extract_per', return_value=10), \
             patch.object(self.parser, '_extract_pbr', return_value=0.5), \
             patch.object(self.parser, '_extract_bps', return_value=2000), \
             patch.object(self.parser, '_extract_equity', return_value=2000000), \
             patch.object(self.parser, '_extract_debt', return_value=1000000), \
             patch.object(self.parser, '_extract_outstanding_shares', return_value=1000000), \
             patch.object(self.parser, '_extract_net_income', return_value=100000), \
             patch.object(self.parser, '_extract_eps', return_value=100), \
             patch.object(self.parser, '_extract_cash', return_value=500000):
            
            # Simulate the call from fetch_edinet_financial_documents.py
            result = self.parser.parse_financial_data(
                b"mock_zip_content",  # This would be the actual ZIP in real usage
                "1234",  # sec_code
                "Test Company",  # filer_name
                "S1234567",  # doc_id
                "2025-03-31",  # period_end
                self.test_date  # issued_date - this is what we're testing
            )
            
            # Verify the issued_date was correctly passed through
            self.assertIsNotNone(result)
            self.assertEqual(result["issuedDate"], self.test_date)
            self.assertIn("retrievedDate", result)
            
            # Verify the dates are different (issued vs retrieved)
            self.assertNotEqual(result["issuedDate"], result["retrievedDate"])


if __name__ == '__main__':
    unittest.main()