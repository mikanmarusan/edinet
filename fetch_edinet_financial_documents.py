#!/usr/bin/env python3
"""
EDINET Daily Data Extraction Tool

Retrieves securities reports submitted on a specific date via EDINET API,
parses XBRL data, and extracts predefined financial metrics.

Usage:
    python tool1.py --date 2025-06-10
"""

import argparse
import json
import os
import sys
import zipfile
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
import time
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re


class EdinetClient:
    """Client for interacting with EDINET API v2"""
    
    BASE_URL = "https://disclosure.edinet-fsa.go.jp/api/v2"
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0
        
    def _wait_for_rate_limit(self):
        """Ensure 1 second delay between API requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def get_documents(self, date: str) -> List[Dict[str, Any]]:
        """
        Retrieve list of documents submitted on specified date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of document metadata
        """
        self._wait_for_rate_limit()
        
        url = f"{self.BASE_URL}/documents.json"
        params = {
            "date": date,
            "type": "2"  # Documents to be submitted
        }
        
        if self.api_key:
            params["Subscription-Key"] = self.api_key
            
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Filter for documents with docTypeCode=120 and secCode exists
            documents = data.get("results", [])
            securities_reports = [
                doc for doc in documents
                if doc.get("docTypeCode") == "120" and doc.get("secCode")
            ]
            
            return securities_reports
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching documents: {e}", file=sys.stderr)
            return []
    
    def download_document(self, doc_id: str) -> Optional[bytes]:
        """
        Download XBRL document by document ID
        
        Args:
            doc_id: Document ID from EDINET
            
        Returns:
            Document content as bytes or None if error
        """
        self._wait_for_rate_limit()
        
        url = f"{self.BASE_URL}/documents/{doc_id}"
        params = {"type": "1"}  # XBRL format
        
        if self.api_key:
            params["Subscription-Key"] = self.api_key
            
        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading document {doc_id}: {e}", file=sys.stderr)
            return None



class XBRLParser:
    """Parser for extracting financial metrics from XBRL documents"""
    
    def __init__(self):
        # 2025 EDINET XBRL namespace prefixes
        self.namespaces = {
            'xbrli': 'http://www.xbrl.org/2003/instance',
            'jpcrp_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor',
            'jppfs_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor',
            'jpigp_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpigp/2024-11-01/jpigp_cor',
            'jpdei_cor': 'http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor',
            'iso4217': 'http://www.xbrl.org/2003/iso4217',
            'xbrldi': 'http://xbrl.org/2006/xbrldi',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
    
    def parse_financial_data(self, xbrl_content: bytes, sec_code: str, filer_name: str, doc_id: str, period_end: str) -> Optional[Dict[str, Any]]:
        """
        Parse XBRL content and extract financial metrics
        
        Args:
            xbrl_content: XBRL document content (ZIP format)
            sec_code: Securities code
            filer_name: Company name
            doc_id: Document ID
            period_end: Period end date
            
        Returns:
            Dictionary with financial metrics or None if parsing fails
        """
        try:
            # Extract XBRL files from ZIP
            xbrl_files = self._extract_xbrl_files(xbrl_content)
            if not xbrl_files:
                return None
            
            # Parse main XBRL instance document
            main_xbrl = self._find_main_xbrl(xbrl_files)
            if not main_xbrl:
                return None
            
            # Parse XML content
            root = ET.fromstring(main_xbrl)
            
            # Convert periodEnd from YYYY-MM-DD to YYYY年MM月期 format
            formatted_period_end = self._format_period_end(period_end)
            
            # Extract financial data
            financial_data = {
                "secCode": sec_code,
                "filerName": filer_name,
                "docID": doc_id,
                "periodEnd": formatted_period_end,
                "characteristic": self._extract_characteristic(root),
                "stockPrice": self._extract_stock_price(root),
                "netSales": self._extract_net_sales(root),
                "employees": self._extract_employees(root),
                "operatingIncome": self._extract_operating_income(root),
                "operatingIncomeRate": None,  # Will be calculated
                "depreciation": self._extract_depreciation(root),
                "ebitda": None,  # Will be calculated
                "ebitdaMargin": None,  # Will be calculated
                "marketCapitalization": self._extract_market_cap(root),
                "per": self._extract_per(root),
                "ev": None,  # Will be calculated
                "evPerEbitda": None,  # Will be calculated
                "pbr": self._extract_pbr(root),
                "equity": self._extract_equity(root),
                "debt": self._extract_debt(root),
                "retrievedDate": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Calculate derived metrics
            financial_data = self._calculate_derived_metrics(financial_data)
            
            return financial_data
            
        except Exception as e:
            print(f"Error parsing XBRL for {sec_code}: {e}", file=sys.stderr)
            return None
    
    def _extract_xbrl_files(self, zip_content: bytes) -> Dict[str, bytes]:
        """Extract XBRL files from ZIP archive"""
        xbrl_files = {}
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_file:
                for file_info in zip_file.filelist:
                    if file_info.filename.endswith(('.xbrl', '.xml')):
                        xbrl_files[file_info.filename] = zip_file.read(file_info.filename)
        except Exception as e:
            print(f"Error extracting ZIP: {e}", file=sys.stderr)
            
        return xbrl_files
    
    def _find_main_xbrl(self, xbrl_files: Dict[str, bytes]) -> Optional[bytes]:
        """Find the main XBRL instance document"""
        # Look for the main XBRL instance file in PublicDoc
        for filename, content in xbrl_files.items():
            if ('PublicDoc' in filename and filename.endswith('.xbrl') and 
                'jpcrp030000-asr' in filename):
                return content
        
        # Fallback: any .xbrl file in PublicDoc
        for filename, content in xbrl_files.items():
            if 'PublicDoc' in filename and filename.endswith('.xbrl'):
                return content
        
        # Last resort: any .xbrl file
        for filename, content in xbrl_files.items():
            if filename.endswith('.xbrl'):
                return content
        
        return None
    
    def _extract_period_end(self, root: ET.Element) -> Optional[str]:
        """Extract fiscal period end date"""
        # Look for period end date in various formats
        period_patterns = [
            './/jppfs:AccountingStandardsDEI',
            './/jpcrp:AccountingStandardsDEI',
            './/dei:DocumentPeriodEndDate'
        ]
        
        for pattern in period_patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                # Extract year and format as Japanese fiscal period
                date_text = elements[0].text
                if date_text:
                    try:
                        date_obj = datetime.strptime(date_text, '%Y-%m-%d')
                        return f"{date_obj.year}年{date_obj.month}月期"
                    except ValueError:
                        pass
        
        # Fallback: extract from context information
        contexts = root.findall('.//xbrl:context', self.namespaces)
        for context in contexts:
            period = context.find('xbrl:period', self.namespaces)
            if period is not None:
                end_date = period.find('xbrl:endDate', self.namespaces)
                if end_date is not None and end_date.text:
                    try:
                        date_obj = datetime.strptime(end_date.text, '%Y-%m-%d')
                        return f"{date_obj.year}年{date_obj.month}月期"
                    except ValueError:
                        pass
        
        return None
    
    def _format_period_end(self, period_end: str) -> str:
        """Convert period end from YYYY-MM-DD to YYYY年MM月期 format"""
        if not period_end:
            return ""
        
        try:
            # Parse the date string (expecting YYYY-MM-DD format)
            date_obj = datetime.strptime(period_end, '%Y-%m-%d')
            
            # Format as YYYY年MM月期 (remove leading zero from month)
            year = date_obj.year
            month = date_obj.month
            return f"{year}年{month}月期"
            
        except ValueError:
            # If parsing fails, return the original string
            return period_end
    
    def _extract_characteristic(self, root: ET.Element) -> Optional[str]:
        """Extract company characteristics/business description"""
        # Look for business description in 2025 taxonomy
        desc_patterns = [
            './/jpcrp_cor:DescriptionOfBusiness',
            './/jpcrp_cor:BusinessDescription',
            './/jpcrp_cor:OutlineOfBusiness',
            './/jppfs_cor:DescriptionOfBusiness'
        ]
        
        for pattern in desc_patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements and elements[0].text:
                # Clean up the text
                text = elements[0].text.strip()
                # Remove extra whitespace and newlines
                text = re.sub(r'\s+', ' ', text)
                return text[:100] + "..." if len(text) > 100 else text
        
        return None
    
    def _extract_numeric_value(self, root: ET.Element, patterns: List[str]) -> Optional[float]:
        """Extract numeric value from XBRL using multiple patterns"""
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                for element in elements:
                    if element.text:
                        try:
                            # Convert to float, handling different formats
                            value = float(element.text.replace(',', ''))
                            return value
                        except ValueError:
                            continue
        return None
    
    def _extract_numeric_value_with_context(self, root: ET.Element, patterns: List[str]) -> Optional[float]:
        """Extract numeric value with priority for current year context"""
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                # Filter and sort elements by context to prefer current year
                current_year_elements = []
                other_elements = []
                
                for element in elements:
                    context_ref = element.get('contextRef', '')
                    if 'CurrentYear' in context_ref:
                        current_year_elements.append(element)
                    else:
                        other_elements.append(element)
                
                # Try current year elements first
                for element in current_year_elements:
                    if element.text:
                        try:
                            return float(element.text.replace(',', ''))
                        except ValueError:
                            continue
                
                # Fallback to other elements
                for element in other_elements:
                    if element.text:
                        try:
                            return float(element.text.replace(',', ''))
                        except ValueError:
                            continue
        return None
    
    def _extract_stock_price(self, root: ET.Element) -> Optional[float]:
        """Extract stock price"""
        patterns = [
            './/jpcrp_cor:StockPrice',
            './/jppfs_cor:StockPrice',
            './/jpcrp_cor:SharePrice',
            './/jppfs_cor:SharePrice'
        ]
        return self._extract_numeric_value(root, patterns)
    
    def _extract_net_sales(self, root: ET.Element) -> Optional[float]:
        """Extract net sales/revenue - prioritize current year"""
        # Look for current year revenue/sales with various patterns
        patterns = [
            './/jpcrp_cor:RevenueIFRSSummaryOfBusinessResults',
            './/jpcrp_cor:NetSalesSummaryOfBusinessResults',
            './/jppfs_cor:NetSales'
        ]
        return self._extract_numeric_value_with_context(root, patterns)
    
    def _extract_employees(self, root: ET.Element) -> Optional[int]:
        """Extract number of employees"""
        patterns = [
            './/jpcrp_cor:NumberOfEmployees',
            './/jppfs_cor:NumberOfEmployees'
        ]
        value = self._extract_numeric_value_with_context(root, patterns)
        return int(value) if value is not None else None
    
    def _extract_operating_income(self, root: ET.Element) -> Optional[float]:
        """Extract operating income"""
        # First try to find elements using direct namespace search
        for elem in root.iter():
            if elem.tag and ('OperatingProfitLoss' in elem.tag or 'OperatingIncome' in elem.tag):
                if elem.text:
                    try:
                        return float(elem.text.replace(',', ''))
                    except ValueError:
                        continue
        
        # Fallback to simple patterns
        patterns = [
            './/jppfs_cor:OperatingIncome'
        ]
        return self._extract_numeric_value_with_context(root, patterns)
    
    def _extract_depreciation(self, root: ET.Element) -> Optional[float]:
        """Extract depreciation expenses"""
        patterns = [
            './/jppfs_cor:DepreciationAndAmortization',
            './/jpcrp_cor:DepreciationAndAmortization'
        ]
        return self._extract_numeric_value_with_context(root, patterns)
    
    def _extract_market_cap(self, root: ET.Element) -> Optional[float]:
        """Extract market capitalization"""
        patterns = [
            './/jpcrp_cor:MarketCapitalization',
            './/jppfs_cor:MarketCapitalization'
        ]
        return self._extract_numeric_value(root, patterns)
    
    def _extract_per(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-earnings ratio"""
        patterns = [
            './/jpcrp_cor:PriceEarningsRatio',
            './/jppfs_cor:PriceEarningsRatio'
        ]
        return self._extract_numeric_value(root, patterns)
    
    def _extract_pbr(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-book ratio"""
        patterns = [
            './/jpcrp_cor:PriceBookValueRatio', 
            './/jppfs_cor:PriceBookValueRatio'
        ]
        return self._extract_numeric_value(root, patterns)
    
    def _extract_equity(self, root: ET.Element) -> Optional[float]:
        """Extract total equity/shareholders' equity"""
        patterns = [
            './/jpigp_cor:EquityIFRS',
            './/jppfs_cor:ShareholdersEquity', 
            './/jpcrp_cor:ShareholdersEquity'
        ]
        return self._extract_numeric_value_with_context(root, patterns)
    
    def _extract_debt(self, root: ET.Element) -> Optional[float]:
        """Extract net interest-bearing debt"""
        patterns = [
            './/jppfs_cor:InterestBearingDebt',
            './/jpcrp_cor:InterestBearingDebt'
        ]
        return self._extract_numeric_value_with_context(root, patterns)
    
    def _calculate_derived_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived financial metrics"""
        try:
            net_sales = financial_data.get('netSales')
            operating_income = financial_data.get('operatingIncome')
            depreciation = financial_data.get('depreciation')
            market_cap = financial_data.get('marketCapitalization')
            debt = financial_data.get('debt', 0)
            
            # Operating income rate
            if net_sales and operating_income and net_sales > 0:
                financial_data['operatingIncomeRate'] = (operating_income / net_sales) * 100
            
            # EBITDA
            if operating_income and depreciation:
                financial_data['ebitda'] = operating_income + depreciation
            
            # EBITDA margin
            if financial_data.get('ebitda') and net_sales and net_sales > 0:
                financial_data['ebitdaMargin'] = (financial_data['ebitda'] / net_sales) * 100
            
            # Enterprise Value (EV)
            if market_cap and debt is not None:
                financial_data['ev'] = market_cap + debt
            
            # EV/EBITDA
            if financial_data.get('ev') and financial_data.get('ebitda') and financial_data['ebitda'] > 0:
                financial_data['evPerEbitda'] = financial_data['ev'] / financial_data['ebitda']
            
        except Exception as e:
            print(f"Error calculating derived metrics: {e}", file=sys.stderr)
        
        return financial_data


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'fetch_edinet_financial_documents_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )


def validate_date_format(date_string: str) -> bool:
    """Validate date format"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def main():
    """Main entry point for tool1"""
    parser = argparse.ArgumentParser(description="Extract financial data from EDINET for a specific date")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--outputdir", required=True, help="Output directory for JSON files")
    parser.add_argument("--api-key", required=True, help="EDINET API key")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retries for failed requests")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting EDINET data extraction for date: {args.date}")
    
    # Validate date format
    if not validate_date_format(args.date):
        logger.error("Date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    try:
        # Initialize clients
        edinet_client = EdinetClient(args.api_key)
        xbrl_parser = XBRLParser()
        
        logger.info(f"Retrieving securities reports for {args.date}...")
        
        # Get list of securities reports for the date
        documents = edinet_client.get_documents(args.date)
        
        if not documents:
            logger.warning(f"No securities reports found for {args.date}")
            return
        
        logger.info(f"Found {len(documents)} securities reports")
        
        # Process each document
        financial_data_list = []
        successful_extractions = 0
        failed_extractions = 0
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get("docID", "")
            sec_code = doc.get("secCode", "")
            # Convert secCode to 4 digits by removing trailing zero if present
            if sec_code and sec_code.endswith('0') and len(sec_code) == 5:
                sec_code = sec_code[:-1]
            filer_name = doc.get("filerName", "")
            period_end = doc.get("periodEnd", "")
            
            logger.info(f"Processing [{i}/{len(documents)}] {filer_name} ({sec_code})...")
            
            retry_count = 0
            success = False
            
            while retry_count < args.max_retries and not success:
                try:
                    # Download XBRL document
                    xbrl_content = edinet_client.download_document(doc_id)
                    if not xbrl_content:
                        logger.warning(f"Failed to download document for {filer_name} ({sec_code})")
                        break
                    
                    # Parse financial data
                    financial_data = xbrl_parser.parse_financial_data(xbrl_content, sec_code, filer_name, doc_id, period_end)
                    if financial_data:
                        financial_data_list.append(financial_data)
                        logger.info(f"Successfully extracted data for {filer_name}")
                        successful_extractions += 1
                        success = True
                    else:
                        logger.warning(f"Failed to parse XBRL data for {filer_name} ({sec_code})")
                        break
                        
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error processing {filer_name} ({sec_code}) - attempt {retry_count}: {e}")
                    
                    if retry_count < args.max_retries:
                        logger.info(f"Retrying in 2 seconds...")
                        time.sleep(2)
                    else:
                        logger.error(f"Max retries exceeded for {filer_name} ({sec_code})")
            
            if not success:
                failed_extractions += 1
        
        # Save results to JSON file
        try:
            os.makedirs(args.outputdir, exist_ok=True)
            output_file = f"{args.outputdir}/{args.date}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(financial_data_list, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(financial_data_list)} company records to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results to file: {e}")
            sys.exit(1)
        
        # Summary
        logger.info(f"Extraction completed!")
        logger.info(f"  Total documents processed: {len(documents)}")
        logger.info(f"  Successful extractions: {successful_extractions}")
        logger.info(f"  Failed extractions: {failed_extractions}")
        logger.info(f"  Output file: {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()