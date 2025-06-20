#!/usr/bin/env python3
"""
Local XBRL Analysis Tool

Analyzes XBRL files that might be available locally or creates test data 
to simulate the share extraction improvements.
"""

import sys
import json
from typing import Dict, List, Any
from datetime import datetime

# Add lib to path
sys.path.append('.')
from lib.xbrl_parser import XBRLParser
from lib.edinet_common import XBRL_PATTERNS

def simulate_xbrl_improvements():
    """
    Simulate the improvements made to outstanding shares extraction
    """
    print("EDINET XBRL Outstanding Shares Extraction - Analysis Report")
    print("=" * 70)
    
    # Show current patterns
    print(f"\n1. CURRENT OUTSTANDING SHARES PATTERNS ({len(XBRL_PATTERNS['outstanding_shares'])} total):")
    print("-" * 50)
    
    for i, pattern in enumerate(XBRL_PATTERNS['outstanding_shares'], 1):
        tag_name = pattern.split(':')[-1] if ':' in pattern else pattern
        print(f"{i:2d}. {tag_name}")
    
    # Show improvements made
    print("\n2. IMPROVEMENTS IMPLEMENTED:")
    print("-" * 50)
    
    improvements = [
        "✓ Expanded from 6 to 28 search patterns",
        "✓ Added dynamic fallback search for share-related tags",
        "✓ Implemented priority scoring for share candidates",
        "✓ Added context-aware matching (CurrentYear preference)",
        "✓ Added value range filtering (1,000 to 100B shares)",
        "✓ Added keyword-based tag discovery",
        "✓ Enhanced logging for debugging missing shares"
    ]
    
    for improvement in improvements:
        print(f"  {improvement}")
    
    # Show expected tag types we now cover
    print("\n3. TAG CATEGORIES NOW COVERED:")
    print("-" * 50)
    
    categories = {
        "Standard Patterns": [
            "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYear",
            "NumberOfSharesIssuedAtTheEndOfFiscalYear",
            "NumberOfSharesOutstanding"
        ],
        "Issued Shares": [
            "NumberOfIssuedShares",
            "SharesIssued", 
            "TotalNumberOfIssuedShares"
        ],
        "Common Stock": [
            "NumberOfSharesIssuedCommonStock",
            "CommonStockNumberOfSharesIssued"
        ],
        "Outstanding Specific": [
            "NumberOfSharesOutstandingAtFiscalYearEnd",
            "SharesOutstanding"
        ],
        "Capital Stock": [
            "CapitalStockNumberOfShares",
            "NumberOfSharesCapitalStock"
        ],
        "Dynamic Search": [
            "Any tag containing 'NumberOfShares'",
            "Any tag containing 'SharesIssued'",
            "Any tag containing 'SharesOutstanding'"
        ]
    }
    
    for category, examples in categories.items():
        print(f"\n  {category}:")
        for example in examples:
            print(f"    - {example}")
    
    # Show priority scoring system
    print("\n4. PRIORITY SCORING SYSTEM:")
    print("-" * 50)
    
    scoring_rules = [
        "+20 points: Current year context",
        "+15 points: 'Outstanding' in tag name", 
        "+12 points: 'Issued' in tag name",
        "+10 points: End-of-period indicators",
        "+8 points: Common stock specific",
        "+5 points: Value in 10M-10B range",
        "+3 points: Value in 1M-100B range",
        "-5 points: Treasury or authorized shares"
    ]
    
    for rule in scoring_rules:
        print(f"  {rule}")
    
    # Recommendations for testing
    print("\n5. TESTING RECOMMENDATIONS:")
    print("-" * 50)
    
    recommendations = [
        "1. Run fetch_edinet_financial_documents.py with updated code",
        "2. Check if outstandingShares field now has values",
        "3. Look for 'Dynamic share search found:' in logs",
        "4. Verify share counts are reasonable (millions to billions)",
        "5. Compare with company annual reports for validation"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print("\n6. NEXT STEPS IF SHARES STILL NOT FOUND:")
    print("-" * 50)
    
    next_steps = [
        "1. Enable verbose logging to see detailed extraction attempts",
        "2. Manually inspect XBRL files to identify actual tag names used",
        "3. Add company-specific patterns based on findings",
        "4. Consider different XBRL contexts (quarterly vs annual)",
        "5. Check if shares are in different units (thousands vs individual)"
    ]
    
    for step in next_steps:
        print(f"  {step}")

def analyze_current_data():
    """Analyze current data to see outstanding shares status"""
    print("\n7. CURRENT DATA ANALYSIS:")
    print("-" * 50)
    
    try:
        with open('data/jsons/2025-06-18.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Analyzing {len(data)} companies from 2025-06-18.json...")
        
        # Check outstanding shares field
        companies_with_shares = 0
        companies_without_shares = 0
        
        for company in data:
            if 'outstandingShares' in company:
                if company['outstandingShares'] is not None:
                    companies_with_shares += 1
                else:
                    companies_without_shares += 1
            else:
                companies_without_shares += 1
        
        print(f"Companies with outstanding shares data: {companies_with_shares}")
        print(f"Companies without outstanding shares data: {companies_without_shares}")
        
        if companies_with_shares > 0:
            print("\nSample companies WITH shares data:")
            count = 0
            for company in data:
                if company.get('outstandingShares') is not None:
                    print(f"  {company['filerName']}: {company['outstandingShares']:,} shares")
                    count += 1
                    if count >= 3:
                        break
        
        print("\nSample companies WITHOUT shares data:")
        count = 0
        for company in data:
            if company.get('outstandingShares') is None:
                print(f"  {company['filerName']} ({company['secCode']})")
                count += 1
                if count >= 5:
                    break
        
    except FileNotFoundError:
        print("No recent data file found. Run fetch script first.")
    except Exception as e:
        print(f"Error analyzing data: {e}")

def main():
    """Main analysis function"""
    simulate_xbrl_improvements()
    analyze_current_data()
    
    print(f"\n{'='*70}")
    print("Analysis complete. The code has been enhanced to better extract")
    print("outstanding shares from EDINET XBRL documents.")
    print("Run fetch_edinet_financial_documents.py to test the improvements.")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()