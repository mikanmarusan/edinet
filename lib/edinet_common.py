#!/usr/bin/env python3
"""
EDINET Common Utilities

Shared utilities, configurations, and logging setup for EDINET tools.
"""

import logging
import sys
import os
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
        './/jpcrp_cor:RevenueIFRSSummaryOfBusinessResults',
        './/jpcrp_cor:NetSalesSummaryOfBusinessResults',
        './/jppfs_cor:NetSales'
    ],
    'employees': [
        './/jpcrp_cor:NumberOfEmployees',
        './/jppfs_cor:NumberOfEmployees'
    ],
    'operating_income': [
        './/jppfs_cor:OperatingIncome'
    ],
    'depreciation': [
        './/jppfs_cor:DepreciationAndAmortization',
        './/jpcrp_cor:DepreciationAndAmortization'
    ],
    'market_cap': [
        './/jpcrp_cor:MarketCapitalization',
        './/jppfs_cor:MarketCapitalization'
    ],
    'per': [
        './/jpcrp_cor:PriceEarningsRatio',
        './/jppfs_cor:PriceEarningsRatio'
    ],
    'pbr': [
        './/jpcrp_cor:PriceBookValueRatio', 
        './/jppfs_cor:PriceBookValueRatio'
    ],
    'equity': [
        './/jpigp_cor:EquityIFRS',
        './/jppfs_cor:ShareholdersEquity', 
        './/jpcrp_cor:ShareholdersEquity'
    ],
    'debt': [
        './/jppfs_cor:InterestBearingDebt',
        './/jpcrp_cor:InterestBearingDebt'
    ],
    'characteristic': [
        './/jpcrp_cor:DescriptionOfBusiness',
        './/jpcrp_cor:BusinessDescription',
        './/jpcrp_cor:OutlineOfBusiness',
        './/jppfs_cor:DescriptionOfBusiness'
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