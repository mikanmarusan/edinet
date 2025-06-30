#!/usr/bin/env python3
"""
EDINET Common Utilities

Shared utilities, configurations, and logging setup for EDINET tools.
"""

import logging
import sys
import os
import yaml
from datetime import datetime
from typing import Optional, Dict, Any


# EDINET API Configuration
EDINET_BASE_URL = "https://disclosure.edinet-fsa.go.jp/api/v2"
RATE_LIMIT_DELAY = 1.0  # seconds
DEFAULT_TIMEOUT = 30  # seconds
DOWNLOAD_TIMEOUT = 60  # seconds

# XBRL Namespace mappings for EDINET 2024-11-01 taxonomy
XBRL_NAMESPACES = {
    'xbrli': 'http://www.xbrl.org/2003/instance',
    'jpcrp_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor',
    'jppfs_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor',
    'jpigp_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpigp/2024-11-01/jpigp_cor',
    'jpdei_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor',
    'iso4217': 'http://www.xbrl.org/2003/iso4217',
    'xbrldi': 'http://xbrl.org/2006/xbrldi',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# XBRL field patterns for financial data extraction
XBRL_PATTERNS = {
    'stock_price': [
        './/jpcrp_cor:StockPrice',
        './/jppfs_cor:StockPrice',
        './/jpcrp_cor:SharePrice',
        './/jppfs_cor:SharePrice'
    ],
    'net_sales': [
        # Primary consolidated patterns
        './/jpcrp_cor:RevenueIFRSSummaryOfBusinessResults',
        './/jpcrp_cor:NetSalesSummaryOfBusinessResults',
        './/jppfs_cor:NetSales',
        
        # Additional consolidated revenue patterns
        './/jpcrp_cor:ConsolidatedNetSales',
        './/jppfs_cor:ConsolidatedNetSales',
        './/jpcrp_cor:ConsolidatedRevenue',
        './/jppfs_cor:ConsolidatedRevenue',
        './/jpcrp_cor:TotalRevenue',
        './/jppfs_cor:TotalRevenue',
        './/jpcrp_cor:OperatingRevenue',
        './/jppfs_cor:OperatingRevenue',
        
        # IFRS patterns
        './/jpcrp_cor:Revenue',
        './/jppfs_cor:Revenue',
        './/jpcrp_cor:RevenueFromContractsWithCustomers',
        './/jppfs_cor:RevenueFromContractsWithCustomers'
    ],
    'employees': [
        # Primary employee patterns
        './/jpcrp_cor:NumberOfEmployees',
        './/jppfs_cor:NumberOfEmployees',
        
        # Consolidated employee patterns
        './/jpcrp_cor:ConsolidatedNumberOfEmployees',
        './/jppfs_cor:ConsolidatedNumberOfEmployees',
        './/jpcrp_cor:TotalNumberOfEmployees',
        './/jppfs_cor:TotalNumberOfEmployees',
        './/jpcrp_cor:NumberOfEmployeesConsolidated',
        './/jppfs_cor:NumberOfEmployeesConsolidated',
        
        # Alternative employee patterns
        './/jpcrp_cor:Employees',
        './/jppfs_cor:Employees',
        './/jpcrp_cor:TotalEmployees',
        './/jppfs_cor:TotalEmployees',
        './/jpcrp_cor:Personnel',
        './/jppfs_cor:Personnel'
    ],
    'operating_income': [
        # Consolidated operating income patterns (priority)
        './/jpcrp_cor:ConsolidatedOperatingIncome',
        './/jppfs_cor:ConsolidatedOperatingIncome',
        './/jpcrp_cor:OperatingIncomeConsolidated',
        './/jppfs_cor:OperatingIncomeConsolidated',
        
        # Standard operating income patterns
        './/jppfs_cor:OperatingIncome',
        './/jpcrp_cor:OperatingIncome',
        './/jppfs_cor:OperatingProfitLoss',
        './/jpcrp_cor:OperatingProfitLoss'
    ],
    'depreciation': [
        # Consolidated depreciation patterns (priority)
        './/jpcrp_cor:ConsolidatedDepreciationAndAmortization',
        './/jppfs_cor:ConsolidatedDepreciationAndAmortization',
        './/jpcrp_cor:DepreciationAndAmortizationConsolidated',
        './/jppfs_cor:DepreciationAndAmortizationConsolidated',
        
        # Standard depreciation patterns
        './/jppfs_cor:DepreciationAndAmortization',
        './/jpcrp_cor:DepreciationAndAmortization',
        './/jppfs_cor:Depreciation',
        './/jpcrp_cor:Depreciation'
    ],
    'market_cap': [
        './/jpcrp_cor:MarketCapitalization',
        './/jppfs_cor:MarketCapitalization'
    ],
    'per': [
        './/jpcrp_cor:PriceEarningsRatio',
        './/jppfs_cor:PriceEarningsRatio',
        './/jpcrp_cor:PriceToEarningsRatio',
        './/jppfs_cor:PriceToEarningsRatio'
    ],
    'pbr': [
        './/jpcrp_cor:PriceBookValueRatio', 
        './/jppfs_cor:PriceBookValueRatio'
    ],
    'bps': [
        # Consolidated BPS patterns (priority)
        './/jpcrp_cor:ConsolidatedBookValuePerShare',
        './/jppfs_cor:ConsolidatedBookValuePerShare',
        './/jpcrp_cor:BookValuePerShareConsolidated',
        './/jppfs_cor:BookValuePerShareConsolidated',
        './/jpcrp_cor:ConsolidatedNetAssetsPerShare',
        './/jppfs_cor:ConsolidatedNetAssetsPerShare',
        
        # Standard BPS patterns
        './/jpcrp_cor:BookValuePerShare',
        './/jppfs_cor:BookValuePerShare',
        './/jpcrp_cor:NetAssetsPerShare',
        './/jppfs_cor:NetAssetsPerShare',
        './/jpcrp_cor:NetBookValuePerShare',
        './/jppfs_cor:NetBookValuePerShare',
        './/jpcrp_cor:ShareholdersEquityPerShare',
        './/jppfs_cor:ShareholdersEquityPerShare'
    ],
    'equity': [
        # Consolidated equity patterns (priority)
        './/jpcrp_cor:ConsolidatedShareholdersEquity',
        './/jppfs_cor:ConsolidatedShareholdersEquity',
        './/jpcrp_cor:ShareholdersEquityConsolidated',
        './/jppfs_cor:ShareholdersEquityConsolidated',
        './/jpigp_cor:ConsolidatedEquityIFRS',
        './/jpcrp_cor:ConsolidatedEquity',
        './/jppfs_cor:ConsolidatedEquity',
        
        # Standard equity patterns
        './/jpigp_cor:EquityIFRS',
        './/jppfs_cor:ShareholdersEquity', 
        './/jpcrp_cor:ShareholdersEquity',
        './/jppfs_cor:Equity',
        './/jpcrp_cor:Equity'
    ],
    'debt': [
        # Consolidated interest-bearing debt patterns (priority)
        './/jpcrp_cor:ConsolidatedInterestBearingDebt',
        './/jppfs_cor:ConsolidatedInterestBearingDebt',
        './/jpcrp_cor:InterestBearingDebtConsolidated',
        './/jppfs_cor:InterestBearingDebtConsolidated',
        './/jpcrp_cor:ConsolidatedTotalInterestBearingDebt',
        './/jppfs_cor:ConsolidatedTotalInterestBearingDebt',
        
        # Consolidated debt patterns
        './/jpcrp_cor:ConsolidatedDebt',
        './/jppfs_cor:ConsolidatedDebt',
        './/jpcrp_cor:ConsolidatedTotalDebt',
        './/jppfs_cor:ConsolidatedTotalDebt',
        './/jpcrp_cor:DebtConsolidated',
        './/jppfs_cor:DebtConsolidated',
        
        # Consolidated borrowings patterns
        './/jpcrp_cor:ConsolidatedBorrowings',
        './/jppfs_cor:ConsolidatedBorrowings',
        './/jpcrp_cor:ConsolidatedTotalBorrowings',
        './/jppfs_cor:ConsolidatedTotalBorrowings',
        './/jpcrp_cor:BorrowingsConsolidated',
        './/jppfs_cor:BorrowingsConsolidated',
        
        # Standard interest-bearing debt patterns
        './/jppfs_cor:InterestBearingDebt',
        './/jpcrp_cor:InterestBearingDebt',
        './/jppfs_cor:TotalInterestBearingDebt',
        './/jpcrp_cor:TotalInterestBearingDebt',
        './/jppfs_cor:InterestBearingLiabilities',
        './/jpcrp_cor:InterestBearingLiabilities',
        
        # Standard debt patterns
        './/jppfs_cor:TotalDebt',
        './/jpcrp_cor:TotalDebt',
        './/jppfs_cor:Debt',
        './/jpcrp_cor:Debt',
        
        # Borrowings patterns
        './/jppfs_cor:Borrowings',
        './/jpcrp_cor:Borrowings',
        './/jppfs_cor:TotalBorrowings',
        './/jpcrp_cor:TotalBorrowings',
        './/jppfs_cor:BorrowingsAndDebt',
        './/jpcrp_cor:BorrowingsAndDebt',
        
        # Loans patterns
        './/jppfs_cor:Loans',
        './/jpcrp_cor:Loans',
        './/jppfs_cor:TotalLoans',
        './/jpcrp_cor:TotalLoans',
        './/jppfs_cor:LoanPayable',
        './/jpcrp_cor:LoanPayable',
        './/jppfs_cor:LoansPayable',
        './/jpcrp_cor:LoansPayable',
        
        # Short-term and long-term debt patterns
        './/jppfs_cor:ShortTermDebt',
        './/jpcrp_cor:ShortTermDebt',
        './/jppfs_cor:LongTermDebt',
        './/jpcrp_cor:LongTermDebt',
        './/jppfs_cor:ShortTermBorrowings',
        './/jpcrp_cor:ShortTermBorrowings',
        './/jppfs_cor:LongTermBorrowings',
        './/jpcrp_cor:LongTermBorrowings',
        './/jppfs_cor:ShortTermLoans',
        './/jpcrp_cor:ShortTermLoans',
        './/jppfs_cor:LongTermLoans',
        './/jpcrp_cor:LongTermLoans',
        
        # Bank loans and bonds patterns
        './/jppfs_cor:BankLoans',
        './/jpcrp_cor:BankLoans',
        './/jppfs_cor:CorporateBonds',
        './/jpcrp_cor:CorporateBonds',
        './/jppfs_cor:BondsPayable',
        './/jpcrp_cor:BondsPayable',
        './/jppfs_cor:NotesPayable',
        './/jpcrp_cor:NotesPayable',
        
        # Financial liabilities patterns (IFRS)
        './/jpigp_cor:FinancialLiabilities',
        './/jpigp_cor:FinancialLiabilitiesIFRS',
        './/jpigp_cor:ConsolidatedFinancialLiabilities',
        './/jpigp_cor:ConsolidatedFinancialLiabilitiesIFRS',
        
        # Net debt patterns
        './/jppfs_cor:NetDebt',
        './/jpcrp_cor:NetDebt',
        './/jppfs_cor:NetInterestBearingDebt',
        './/jpcrp_cor:NetInterestBearingDebt',
        './/jppfs_cor:ConsolidatedNetDebt',
        './/jpcrp_cor:ConsolidatedNetDebt',
        './/jppfs_cor:ConsolidatedNetInterestBearingDebt',
        './/jpcrp_cor:ConsolidatedNetInterestBearingDebt'
    ],
    'characteristic': [
        # Primary business description patterns
        './/jpcrp_cor:DescriptionOfBusiness',
        './/jpcrp_cor:BusinessDescription',
        './/jpcrp_cor:OutlineOfBusiness',
        './/jppfs_cor:DescriptionOfBusiness',
        './/jppfs_cor:BusinessDescription',
        './/jppfs_cor:OutlineOfBusiness',
        
        # Business overview patterns
        './/jpcrp_cor:BusinessOverview',
        './/jppfs_cor:BusinessOverview',
        './/jpcrp_cor:OverviewOfBusiness',
        './/jppfs_cor:OverviewOfBusiness',
        './/jpcrp_cor:BusinessSummary',
        './/jppfs_cor:BusinessSummary',
        
        # Business content patterns
        './/jpcrp_cor:BusinessContent',
        './/jppfs_cor:BusinessContent',
        './/jpcrp_cor:ContentOfBusiness',
        './/jppfs_cor:ContentOfBusiness',
        './/jpcrp_cor:NatureOfBusiness',
        './/jppfs_cor:NatureOfBusiness',
        
        # Main business patterns
        './/jpcrp_cor:MainBusiness',
        './/jppfs_cor:MainBusiness',
        './/jpcrp_cor:PrincipalBusiness',
        './/jppfs_cor:PrincipalBusiness',
        './/jpcrp_cor:CoreBusiness',
        './/jppfs_cor:CoreBusiness',
        
        # Company profile patterns
        './/jpcrp_cor:CompanyProfile',
        './/jppfs_cor:CompanyProfile',
        './/jpcrp_cor:CorporateProfile',
        './/jppfs_cor:CorporateProfile',
        
        # Business activities patterns
        './/jpcrp_cor:BusinessActivities',
        './/jppfs_cor:BusinessActivities',
        './/jpcrp_cor:ActivitiesOfBusiness',
        './/jppfs_cor:ActivitiesOfBusiness'
    ],
    'outstanding_shares': [
        # Priority 1: Total issued shares from summary of business results (most authoritative)
        './/jpcrp_cor:TotalNumberOfIssuedSharesSummaryOfBusinessResults',
        './/jppfs_cor:TotalNumberOfIssuedSharesSummaryOfBusinessResults',
        
        # Priority 2: Total issued shares (general patterns)
        './/jpcrp_cor:TotalNumberOfIssuedShares',
        './/jppfs_cor:TotalNumberOfIssuedShares',
        './/jpcrp_cor:TotalNumberOfSharesIssued',
        './/jppfs_cor:TotalNumberOfSharesIssued',
        
        # Issued shares at end of fiscal year (without treasury stock mention)
        './/jpcrp_cor:NumberOfSharesIssuedAtTheEndOfFiscalYear',
        './/jppfs_cor:NumberOfSharesIssuedAtTheEndOfFiscalYear',
        './/jpcrp_cor:NumberOfIssuedSharesAtTheEndOfFiscalYear',
        './/jppfs_cor:NumberOfIssuedSharesAtTheEndOfFiscalYear',
        
        # Standard issued shares patterns
        './/jpcrp_cor:NumberOfIssuedShares',
        './/jppfs_cor:NumberOfIssuedShares',
        './/jpcrp_cor:SharesIssued',
        './/jppfs_cor:SharesIssued',
        './/jpcrp_cor:IssuedShares',
        './/jppfs_cor:IssuedShares',
        
        # Common stock specific patterns
        './/jpcrp_cor:NumberOfSharesIssuedCommonStock',
        './/jppfs_cor:NumberOfSharesIssuedCommonStock',
        './/jpcrp_cor:CommonStockNumberOfSharesIssued',
        './/jppfs_cor:CommonStockNumberOfSharesIssued',
        './/jpcrp_cor:CommonStockSharesIssued',
        './/jppfs_cor:CommonStockSharesIssued',
        
        # Capital stock related patterns
        './/jpcrp_cor:CapitalStockNumberOfShares',
        './/jppfs_cor:CapitalStockNumberOfShares',
        './/jpcrp_cor:NumberOfSharesCapitalStock',
        './/jppfs_cor:NumberOfSharesCapitalStock',
        
        # Outstanding shares patterns (lower priority as these might exclude treasury stock)
        './/jpcrp_cor:NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYear',
        './/jppfs_cor:NumberOfIssuedAndOutstandingShares',
        './/jpcrp_cor:NumberOfSharesOutstanding',
        './/jppfs_cor:NumberOfSharesOutstanding',
        './/jpcrp_cor:SharesOutstanding',
        './/jppfs_cor:SharesOutstanding',
        './/jpcrp_cor:NumberOfSharesOutstandingAtFiscalYearEnd',
        './/jppfs_cor:NumberOfSharesOutstandingAtFiscalYearEnd',
        
        # Patterns that explicitly include treasury stock (lowest priority)
        './/jpcrp_cor:NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock',
        './/jpcrp_cor:NumberOfSharesOutstandingIncludingTreasuryStock'
    ],
    'eps_basic': [
        # Consolidated basic EPS patterns (priority)
        './/jpcrp_cor:ConsolidatedBasicEarningsPerShare',
        './/jppfs_cor:ConsolidatedBasicEarningsPerShare',
        './/jpcrp_cor:BasicEarningsPerShareConsolidated',
        './/jppfs_cor:BasicEarningsPerShareConsolidated',
        './/jpcrp_cor:ConsolidatedBasicNetIncomePerShare',
        './/jppfs_cor:ConsolidatedBasicNetIncomePerShare',
        
        # Standard basic EPS patterns
        './/jpcrp_cor:BasicEarningsPerShare',
        './/jppfs_cor:BasicEarningsPerShare',
        './/jpcrp_cor:EarningsPerShareBasic',
        './/jppfs_cor:EarningsPerShareBasic',
        './/jpcrp_cor:BasicNetIncomePerShare',
        './/jppfs_cor:BasicNetIncomePerShare',
        './/jpcrp_cor:NetIncomePerShareBasic',
        './/jppfs_cor:NetIncomePerShareBasic'
    ],
    'eps_diluted': [
        # Consolidated diluted EPS patterns (priority)
        './/jpcrp_cor:ConsolidatedDilutedEarningsPerShare',
        './/jppfs_cor:ConsolidatedDilutedEarningsPerShare',
        './/jpcrp_cor:DilutedEarningsPerShareConsolidated',
        './/jppfs_cor:DilutedEarningsPerShareConsolidated',
        './/jpcrp_cor:ConsolidatedDilutedNetIncomePerShare',
        './/jppfs_cor:ConsolidatedDilutedNetIncomePerShare',
        
        # Standard diluted EPS patterns
        './/jpcrp_cor:DilutedEarningsPerShare',
        './/jppfs_cor:DilutedEarningsPerShare',
        './/jpcrp_cor:EarningsPerShareDiluted',
        './/jppfs_cor:EarningsPerShareDiluted',
        './/jpcrp_cor:DilutedNetIncomePerShare',
        './/jppfs_cor:DilutedNetIncomePerShare',
        './/jpcrp_cor:NetIncomePerShareDiluted',
        './/jppfs_cor:NetIncomePerShareDiluted'
    ],
    'net_income': [
        # Consolidated net income patterns (priority)
        './/jpcrp_cor:ConsolidatedNetIncomeLoss',
        './/jppfs_cor:ConsolidatedNetIncomeLoss',
        './/jpcrp_cor:NetIncomeLossConsolidated',
        './/jppfs_cor:NetIncomeLossConsolidated',
        './/jpcrp_cor:ConsolidatedProfitLoss',
        './/jppfs_cor:ConsolidatedProfitLoss',
        './/jpcrp_cor:ConsolidatedNetIncomeAttributableToOwnersOfParent',
        './/jppfs_cor:ConsolidatedNetIncomeAttributableToOwnersOfParent',
        
        # Standard net income patterns
        './/jpcrp_cor:NetIncomeLoss',
        './/jppfs_cor:NetIncomeLoss',
        './/jpcrp_cor:ProfitLoss',
        './/jppfs_cor:ProfitLoss',
        './/jpcrp_cor:NetIncomeAttributableToOwnersOfParent',
        './/jppfs_cor:NetIncomeAttributableToOwnersOfParent',
        './/jpcrp_cor:NetIncomeAttributableToShareholdersOfParentCompany',
        './/jppfs_cor:NetIncomeAttributableToShareholdersOfParentCompany',
        './/jpcrp_cor:NetIncomeAttributableToOwnersOfTheParent',
        './/jppfs_cor:NetIncomeAttributableToOwnersOfTheParent'
    ],
    'cash': [
        # Consolidated cash and cash equivalents patterns (priority)
        './/jpcrp_cor:ConsolidatedCashAndCashEquivalents',
        './/jppfs_cor:ConsolidatedCashAndCashEquivalents',
        './/jpcrp_cor:CashAndCashEquivalentsConsolidated',
        './/jppfs_cor:CashAndCashEquivalentsConsolidated',
        './/jpcrp_cor:ConsolidatedCashAndCashEquivalentsAtEndOfPeriod',
        './/jppfs_cor:ConsolidatedCashAndCashEquivalentsAtEndOfPeriod',
        
        # Standard cash and cash equivalents patterns
        './/jpcrp_cor:CashAndCashEquivalents',
        './/jppfs_cor:CashAndCashEquivalents',
        './/jpcrp_cor:CashAndCashEquivalentsAtEndOfPeriod',
        './/jppfs_cor:CashAndCashEquivalentsAtEndOfPeriod',
        './/jpcrp_cor:CashAndCashEquivalentsAtEndOfFiscalYear',
        './/jppfs_cor:CashAndCashEquivalentsAtEndOfFiscalYear',
        
        # Cash balance patterns
        './/jpcrp_cor:CashAndDeposits',
        './/jppfs_cor:CashAndDeposits',
        './/jpcrp_cor:CashAndCashEquivalentsBalanceAtEndOfPeriod',
        './/jppfs_cor:CashAndCashEquivalentsBalanceAtEndOfPeriod',
        './/jpcrp_cor:CashAndEquivalents',
        './/jppfs_cor:CashAndEquivalents',
        
        # Short-term investments included in cash equivalents
        './/jpcrp_cor:CashDepositsAndShortTermInvestments',
        './/jppfs_cor:CashDepositsAndShortTermInvestments',
        './/jpcrp_cor:CashAndShortTermInvestments',
        './/jppfs_cor:CashAndShortTermInvestments'
    ]
}


def setup_logging(script_name: str, verbose: bool = False) -> logging.Logger:
    """
    Setup logging configuration for EDINET tools
    
    Args:
        script_name: Name of the script for log file naming
        verbose: Enable debug level logging
        
    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_filename = f"{script_name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def validate_date_format(date_string: str) -> bool:
    """
    Validate date format (YYYY-MM-DD)
    
    Args:
        date_string: Date string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_period_end(period_end: str) -> str:
    """
    Convert period end from YYYY-MM-DD to YYYY年MM月期 format
    
    Args:
        period_end: Period end date in YYYY-MM-DD format
        
    Returns:
        Formatted period end string
    """
    if not period_end:
        return ""
    
    try:
        date_obj = datetime.strptime(period_end, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month
        return f"{year}年{month}月期"
    except ValueError:
        return period_end


def normalize_securities_code(sec_code: str) -> str:
    """
    Normalize securities code to 4-digit format
    
    Args:
        sec_code: Securities code (may be 4 or 5 digits)
        
    Returns:
        4-digit securities code
    """
    if not sec_code:
        return ""
    
    # Remove trailing zero from 5-digit codes
    if sec_code.endswith('0') and len(sec_code) == 5:
        return sec_code[:-1]
    
    return sec_code


def ensure_output_directory(output_path: str) -> bool:
    """
    Ensure output directory exists
    
    Args:
        output_path: Output file or directory path
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        directory = os.path.dirname(output_path) if os.path.splitext(output_path)[1] else output_path
        if directory:
            os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


class EdinetError(Exception):
    """Base exception for EDINET-related errors"""
    pass


class EdinetAPIError(EdinetError):
    """Exception for EDINET API-related errors"""
    pass


class XBRLParsingError(EdinetError):
    """Exception for XBRL parsing-related errors"""
    pass


# Cache for stock exchange mapping
_stock_exchange_mapping_cache = None


def get_stock_exchange_code(sec_code: str) -> str:
    """
    Get the stock exchange code for a given security code
    
    Args:
        sec_code: Securities code (4-digit)
        
    Returns:
        Stock exchange code: 'T' (Tokyo), 'N' (Nagoya), 'F' (Fukuoka), or 'S' (Sapporo)
    """
    global _stock_exchange_mapping_cache
    
    # Load mapping from YAML file if not cached
    if _stock_exchange_mapping_cache is None:
        try:
            # Get the path to the config file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, 'config', 'stock_exchange_mapping.yml')
            
            # Load the YAML file
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                _stock_exchange_mapping_cache = data.get('stock_exchanges', {})
        except Exception as e:
            # If loading fails, use empty mapping (all will default to Tokyo)
            print(f"Warning: Could not load stock exchange mapping: {e}")
            _stock_exchange_mapping_cache = {}
    
    # Look up the security code in the mapping
    # Return the mapped exchange code, or 'T' (Tokyo) as default
    return _stock_exchange_mapping_cache.get(sec_code, 'T')