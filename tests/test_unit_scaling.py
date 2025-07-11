#!/usr/bin/env python3
"""
Test XBRL parser unit scaling functionality
"""

import unittest
import xml.etree.ElementTree as ET
from lib.xbrl_parser import XBRLParser


class TestXBRLParserUnitScaling(unittest.TestCase):
    """Test unit scaling functionality in XBRL parser"""
    
    def setUp(self):
        self.parser = XBRLParser()
    
    def test_share_unit_scaling_thousand(self):
        """Test scaling for shares in thousands"""
        # Test data with thousand shares unit
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares_thousand">
    <xbrli:measure>千株</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="shares_thousand">2780021.8</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should scale from thousand shares
        self.assertAlmostEqual(value, 2780021800.0, delta=1)
    
    def test_share_unit_scaling_ten_thousand(self):
        """Test scaling for shares in ten thousands (万株)"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares_man">
    <xbrli:measure>万株</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="shares_man">134441.8</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should scale from ten thousand shares
        self.assertAlmostEqual(value, 1344418000.0, delta=1)
    
    def test_share_unit_scaling_hundred_million(self):
        """Test scaling for shares in hundred millions (億株)"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares_oku">
    <xbrli:measure>億株</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="shares_oku">14.67053490</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should scale from hundred million shares
        self.assertAlmostEqual(value, 1467053490.0, delta=1)
    
    def test_unit_shares_scaling(self):
        """Test scaling for unit shares (単元株)"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="unit_shares">
    <xbrli:measure>単元株</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="unit_shares">102051</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should scale from unit shares (100 shares per unit)
        self.assertAlmostEqual(value, 10205100.0, delta=1)
    
    def test_english_thousand_shares(self):
        """Test scaling for English thousand shares notation"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares_000">
    <xbrli:measure>shares(000s)</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="shares_000">324050</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should scale from thousand shares notation
        self.assertAlmostEqual(value, 324050000.0, delta=1)
    
    def test_market_cap_trillion_yen(self):
        """Test scaling for market cap in trillion yen"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="trillion_yen">
    <xbrli:measure>兆円</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:MarketCapitalization contextRef="CurrentYear" unitRef="trillion_yen">47.5</jpcrp_cor:MarketCapitalization>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:MarketCapitalization']
        )
        
        # Should scale from trillion yen
        self.assertAlmostEqual(value, 47500000000000.0, delta=1000000)
    
    def test_no_unit_scaling(self):
        """Test that normal shares without unit scaling are not modified"""
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares">
    <xbrli:measure>shares</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:TotalNumberOfSharesIssued contextRef="CurrentYear" unitRef="shares">1000000</jpcrp_cor:TotalNumberOfSharesIssued>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:TotalNumberOfSharesIssued']
        )
        
        # Should not scale normal shares
        self.assertEqual(value, 1000000.0)
    
    def test_toyota_total_shares_including_treasury(self):
        """Test Toyota's total issued shares including treasury stock"""
        # Toyota's actual total issued shares (including treasury stock) is approximately 16.3 billion
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor">
  <xbrli:unit id="shares_thousand">
    <xbrli:measure>千株</xbrli:measure>
  </xbrli:unit>
  <jpcrp_cor:NumberOfIssuedAndOutstandingSharesAtEndOfFiscalYearIncludingTreasuryStock 
      contextRef="CurrentYear" unitRef="shares_thousand">16314987.460</jpcrp_cor:NumberOfIssuedAndOutstandingSharesAtEndOfFiscalYearIncludingTreasuryStock>
</xbrl>'''
        
        root = ET.fromstring(test_xml)
        value = self.parser.data_extractor.extract_numeric_value_with_context(
            root, ['.//jpcrp_cor:NumberOfIssuedAndOutstandingSharesAtEndOfFiscalYearIncludingTreasuryStock']
        )
        
        # Should scale from thousand shares to actual shares
        self.assertAlmostEqual(value, 16314987460.0, delta=1)


if __name__ == '__main__':
    unittest.main()