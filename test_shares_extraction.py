#!/usr/bin/env python3
"""
Test Outstanding Shares Extraction

Creates mock XBRL data to test the improved shares extraction logic.
"""

import xml.etree.ElementTree as ET
import sys
from typing import Optional

# Add lib to path
sys.path.append('.')
from lib.xbrl_parser import XBRLParser

def create_mock_xbrl_with_shares() -> str:
    """Create mock XBRL content with share information"""
    
    xbrl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor"
      xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor">
    
    <!-- Standard financial data -->
    <jpcrp_cor:NetSalesSummaryOfBusinessResults contextRef="CurrentYearDuration">1000000000</jpcrp_cor:NetSalesSummaryOfBusinessResults>
    <jpcrp_cor:NumberOfEmployees contextRef="CurrentYearInstant">1500</jpcrp_cor:NumberOfEmployees>
    <jppfs_cor:ShareholdersEquity contextRef="CurrentYearInstant">5000000000</jppfs_cor:ShareholdersEquity>
    
    <!-- Mock outstanding shares data using different patterns -->
    <jpcrp_cor:NumberOfIssuedShares contextRef="CurrentYearInstant">50000000</jpcrp_cor:NumberOfIssuedShares>
    <jpcrp_cor:NumberOfSharesOutstanding contextRef="CurrentYearInstant">48000000</jpcrp_cor:NumberOfSharesOutstanding>
    <jpcrp_cor:SharesIssuedCommonStock contextRef="CurrentYearInstant">50000000</jpcrp_cor:SharesIssuedCommonStock>
    
    <!-- Additional test data that should be found by dynamic search -->
    <jpcrp_cor:CommonStockSharesIssued contextRef="CurrentYearInstant">50000000</jpcrp_cor:CommonStockSharesIssued>
    <jppfs_cor:TotalNumberOfIssuedSharesCommon contextRef="CurrentYearInstant">50000000</jppfs_cor:TotalNumberOfIssuedSharesCommon>
    
    <!-- Data that should get lower priority -->
    <jpcrp_cor:TreasuryStockShares contextRef="CurrentYearInstant">2000000</jpcrp_cor:TreasuryStockShares>
    <jpcrp_cor:NumberOfAuthorizedShares contextRef="CurrentYearInstant">100000000</jpcrp_cor:NumberOfAuthorizedShares>
    
    <!-- Context definitions -->
    <xbrli:context id="CurrentYearInstant">
        <xbrli:entity>
            <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</xbrli:identifier>
        </xbrli:entity>
        <xbrli:period>
            <xbrli:instant>2025-03-31</xbrli:instant>
        </xbrli:period>
    </xbrli:context>
    
    <xbrli:context id="CurrentYearDuration">
        <xbrli:entity>
            <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</xbrli:identifier>
        </xbrli:entity>
        <xbrli:period>
            <xbrli:startDate>2024-04-01</xbrli:startDate>
            <xbrli:endDate>2025-03-31</xbrli:endDate>
        </xbrli:period>
    </xbrli:context>
</xbrl>'''

    return xbrl_content

def create_mock_xbrl_no_standard_patterns() -> str:
    """Create mock XBRL with non-standard share tags"""
    
    xbrl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor"
      xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor">
    
    <!-- Standard financial data -->
    <jpcrp_cor:NetSalesSummaryOfBusinessResults contextRef="CurrentYearDuration">2000000000</jpcrp_cor:NetSalesSummaryOfBusinessResults>
    <jpcrp_cor:NumberOfEmployees contextRef="CurrentYearInstant">2500</jpcrp_cor:NumberOfEmployees>
    
    <!-- Non-standard share tags that should be found by dynamic search -->
    <jpcrp_cor:IssuedSharesCommonStock contextRef="CurrentYearInstant">75000000</jpcrp_cor:IssuedSharesCommonStock>
    <jppfs_cor:NumberOfSharesInCirculation contextRef="CurrentYearInstant">73000000</jppfs_cor:NumberOfSharesInCirculation>
    <jpcrp_cor:OutstandingSharesEndOfPeriod contextRef="CurrentYearInstant">73000000</jpcrp_cor:OutstandingSharesEndOfPeriod>
    
    <!-- Some noise data -->
    <jpcrp_cor:EmployeeCount contextRef="CurrentYearInstant">2500</jpcrp_cor:EmployeeCount>
    <jpcrp_cor:CompanyName contextRef="CurrentYearInstant">Test Company</jpcrp_cor:CompanyName>
    
    <!-- Context definitions -->
    <xbrli:context id="CurrentYearInstant">
        <xbrli:entity>
            <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E67890</xbrli:identifier>
        </xbrli:entity>
        <xbrli:period>
            <xbrli:instant>2025-03-31</xbrli:instant>
        </xbrli:period>
    </xbrli:context>
    
    <xbrli:context id="CurrentYearDuration">
        <xbrli:entity>
            <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E67890</xbrli:identifier>
        </xbrli:entity>
        <xbrli:period>
            <xbrli:startDate>2024-04-01</xbrli:startDate>
            <xbrli:endDate>2025-03-31</xbrli:endDate>
        </xbrli:period>
    </xbrli:context>
</xbrl>'''

    return xbrl_content

def test_shares_extraction():
    """Test the improved shares extraction logic"""
    
    print("Testing Outstanding Shares Extraction Logic")
    print("=" * 50)
    
    parser = XBRLParser()
    
    # Test 1: XBRL with standard patterns
    print("\nTest 1: XBRL with standard share patterns")
    print("-" * 40)
    
    xbrl_content1 = create_mock_xbrl_with_shares()
    root1 = ET.fromstring(xbrl_content1)
    
    # Test standard pattern extraction
    shares1 = parser._extract_outstanding_shares(root1)
    print(f"Extracted shares (standard patterns): {shares1:,} shares" if shares1 else "No shares found")
    
    # Test 2: XBRL with non-standard patterns (should use dynamic search)
    print("\nTest 2: XBRL with non-standard share patterns")
    print("-" * 40)
    
    xbrl_content2 = create_mock_xbrl_no_standard_patterns()
    root2 = ET.fromstring(xbrl_content2)
    
    shares2 = parser._extract_outstanding_shares(root2)
    print(f"Extracted shares (dynamic search): {shares2:,} shares" if shares2 else "No shares found")
    
    # Test 3: Test dynamic search directly
    print("\nTest 3: Direct dynamic search test")
    print("-" * 40)
    
    dynamic_shares1 = parser._dynamic_search_shares(root1)
    print(f"Dynamic search on test 1: {dynamic_shares1:,} shares" if dynamic_shares1 else "No shares found")
    
    dynamic_shares2 = parser._dynamic_search_shares(root2)  
    print(f"Dynamic search on test 2: {dynamic_shares2:,} shares" if dynamic_shares2 else "No shares found")
    
    # Test 4: Show what tags were found
    print("\nTest 4: Share-related tags found in test data")
    print("-" * 40)
    
    def show_share_tags(root, test_name):
        print(f"\n{test_name} share-related elements:")
        share_keywords = ['Share', 'Stock', 'Issued', 'Outstanding', 'Number']
        
        found_tags = []
        for elem in root.iter():
            if elem.tag and elem.text:
                local_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                for keyword in share_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            value = float(elem.text.replace(',', ''))
                            context = elem.get('contextRef', '')
                            found_tags.append((local_name, value, context))
                        except ValueError:
                            pass
                        break
        
        for i, (tag, value, context) in enumerate(found_tags, 1):
            print(f"  {i}. {tag}: {value:,.0f} (context: {context})")
        
        return found_tags
    
    tags1 = show_share_tags(root1, "Test 1")
    tags2 = show_share_tags(root2, "Test 2")
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Test 1 - Standard patterns: {len(tags1)} share tags found, extracted: {shares1}")
    print(f"Test 2 - Dynamic search: {len(tags2)} share tags found, extracted: {shares2}")
    
    if shares1 and shares2:
        print("\n✅ SUCCESS: Both standard and dynamic extraction working!")
    elif shares1:
        print("\n⚠️  PARTIAL: Only standard patterns working")
    elif shares2:
        print("\n⚠️  PARTIAL: Only dynamic search working")
    else:
        print("\n❌ FAILURE: No shares extracted")
    
    print("\nThe improved extraction logic should now work better with real EDINET data.")

if __name__ == "__main__":
    test_shares_extraction()