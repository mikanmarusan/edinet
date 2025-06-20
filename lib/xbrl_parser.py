#!/usr/bin/env python3
"""
XBRL Parser Module

Specialized parser for extracting financial metrics from EDINET XBRL documents.
"""

import xml.etree.ElementTree as ET
import zipfile
import io
import re
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

from .edinet_common import XBRL_NAMESPACES, XBRL_PATTERNS, XBRLParsingError, format_period_end


class XBRLExtractor:
    """Handles XBRL file extraction from ZIP archives"""
    
    def extract_files(self, zip_content: bytes) -> Dict[str, bytes]:
        """
        Extract XBRL files from ZIP archive
        
        Args:
            zip_content: ZIP file content as bytes
            
        Returns:
            Dictionary mapping filenames to file contents
            
        Raises:
            XBRLParsingError: If extraction fails
        """
        xbrl_files = {}
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_file:
                for file_info in zip_file.filelist:
                    if file_info.filename.endswith(('.xbrl', '.xml')):
                        xbrl_files[file_info.filename] = zip_file.read(file_info.filename)
        except Exception as e:
            raise XBRLParsingError(f"Failed to extract ZIP contents: {e}")
            
        return xbrl_files
    
    def find_main_xbrl(self, xbrl_files: Dict[str, bytes]) -> Optional[bytes]:
        """
        Find the main XBRL instance document
        
        Args:
            xbrl_files: Dictionary of XBRL files
            
        Returns:
            Main XBRL document content or None
        """
        # Priority 1: Main XBRL instance file in PublicDoc
        for filename, content in xbrl_files.items():
            if ('PublicDoc' in filename and filename.endswith('.xbrl') and 
                'jpcrp030000-asr' in filename):
                return content
        
        # Priority 2: Any .xbrl file in PublicDoc
        for filename, content in xbrl_files.items():
            if 'PublicDoc' in filename and filename.endswith('.xbrl'):
                return content
        
        # Priority 3: Any .xbrl file
        for filename, content in xbrl_files.items():
            if filename.endswith('.xbrl'):
                return content
        
        return None


class FinancialDataExtractor:
    """Extracts financial data from parsed XBRL documents"""
    
    def __init__(self):
        self.namespaces = XBRL_NAMESPACES
        self.patterns = XBRL_PATTERNS
    
    def extract_numeric_value(self, root: ET.Element, patterns: List[str]) -> Optional[float]:
        """
        Extract numeric value from XBRL using multiple patterns
        
        Args:
            root: XBRL root element
            patterns: List of XPath patterns to try
            
        Returns:
            Extracted numeric value or None
        """
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                for element in elements:
                    if element.text:
                        try:
                            return float(element.text.replace(',', ''))
                        except ValueError:
                            continue
        return None
    
    def extract_numeric_value_with_context(self, root: ET.Element, patterns: List[str]) -> Optional[float]:
        """
        Extract numeric value with priority for current year context
        
        Args:
            root: XBRL root element
            patterns: List of XPath patterns to try
            
        Returns:
            Extracted numeric value or None
        """
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                # Separate current year and other elements
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
    
    def extract_text_value(self, root: ET.Element, patterns: List[str], max_length: int = 100) -> Optional[str]:
        """
        Extract text value from XBRL
        
        Args:
            root: XBRL root element
            patterns: List of XPath patterns to try
            max_length: Maximum text length
            
        Returns:
            Extracted text value or None
        """
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements and elements[0].text:
                text = elements[0].text.strip()
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                return text[:max_length] + "..." if len(text) > max_length else text
        return None
    
    def extract_operating_income_special(self, root: ET.Element) -> Optional[float]:
        """
        Special extraction for operating income using tag search with context prioritization
        
        Args:
            root: XBRL root element
            
        Returns:
            Operating income value or None
        """
        # Collect operating income elements
        operating_income_elements = []
        for elem in root.iter():
            if elem.tag and ('OperatingProfitLoss' in elem.tag or 'OperatingIncome' in elem.tag):
                if elem.text:
                    operating_income_elements.append(elem)
        
        if operating_income_elements:
            # Separate current year and other elements
            current_year_elements = []
            other_elements = []
            
            for element in operating_income_elements:
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
        
        # Fallback to pattern-based search
        return self.extract_numeric_value_with_context(root, self.patterns['operating_income'])


class MetricsCalculator:
    """Calculates derived financial metrics"""
    
    @staticmethod
    def calculate_derived_metrics(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate derived financial metrics
        
        Args:
            financial_data: Dictionary with base financial data
            
        Returns:
            Financial data with calculated derived metrics
        """
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


class XBRLParser:
    """Main XBRL parser for EDINET financial documents"""
    
    def __init__(self):
        self.extractor = XBRLExtractor()
        self.data_extractor = FinancialDataExtractor()
        self.calculator = MetricsCalculator()
    
    def parse_financial_data(self, xbrl_content: bytes, sec_code: str, 
                           filer_name: str, doc_id: str, period_end: str) -> Optional[Dict[str, Any]]:
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
            # Extract XBRL files
            xbrl_files = self.extractor.extract_files(xbrl_content)
            if not xbrl_files:
                raise XBRLParsingError("No XBRL files found in ZIP")
            
            # Find main XBRL document
            main_xbrl = self.extractor.find_main_xbrl(xbrl_files)
            if not main_xbrl:
                raise XBRLParsingError("No main XBRL document found")
            
            # Parse XML content
            root = ET.fromstring(main_xbrl)
            
            # Build financial data structure
            financial_data = self._build_financial_data_structure(
                root, sec_code, filer_name, doc_id, period_end
            )
            
            # Calculate derived metrics
            financial_data = self.calculator.calculate_derived_metrics(financial_data)
            
            return financial_data
            
        except XBRLParsingError:
            raise
        except Exception as e:
            raise XBRLParsingError(f"Error parsing XBRL for {sec_code}: {e}")
    
    def _build_financial_data_structure(self, root: ET.Element, sec_code: str,
                                      filer_name: str, doc_id: str, period_end: str) -> Dict[str, Any]:
        """
        Build the financial data structure from XBRL data
        
        Args:
            root: XBRL root element
            sec_code: Securities code
            filer_name: Company name
            doc_id: Document ID
            period_end: Period end date
            
        Returns:
            Financial data dictionary
        """
        return {
            "secCode": sec_code,
            "filerName": filer_name,
            "docID": doc_id,
            "docPdfURL": f"https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/{doc_id}.pdf",
            "yahooURL": f"https://finance.yahoo.co.jp/quote/{sec_code}.T",
            "periodEnd": format_period_end(period_end),
            "characteristic": self._extract_characteristic(root),
            "stockPrice": self._extract_stock_price(root),
            "netSales": self._extract_net_sales(root),
            "employees": self._extract_employees(root),
            "operatingIncome": self._extract_operating_income(root),
            "operatingIncomeRate": None,  # Calculated later
            "depreciation": self._extract_depreciation(root),
            "ebitda": None,  # Calculated later
            "ebitdaMargin": None,  # Calculated later
            "marketCapitalization": self._extract_market_cap(root),
            "per": self._extract_per(root),
            "ev": None,  # Calculated later
            "evPerEbitda": None,  # Calculated later
            "pbr": self._extract_pbr(root),
            "equity": self._extract_equity(root),
            "debt": self._extract_debt(root),
            "outstandingShares": self._extract_outstanding_shares(root),
            "retrievedDate": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _extract_characteristic(self, root: ET.Element) -> Optional[str]:
        """Extract company characteristics/business description"""
        return self.data_extractor.extract_text_value(root, self.data_extractor.patterns['characteristic'])
    
    def _extract_stock_price(self, root: ET.Element) -> Optional[float]:
        """Extract stock price"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['stock_price'])
    
    def _extract_net_sales(self, root: ET.Element) -> Optional[float]:
        """Extract net sales/revenue"""
        return self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['net_sales'])
    
    def _extract_employees(self, root: ET.Element) -> Optional[int]:
        """Extract number of employees"""
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['employees'])
        return int(value) if value is not None else None
    
    def _extract_operating_income(self, root: ET.Element) -> Optional[float]:
        """Extract operating income"""
        return self.data_extractor.extract_operating_income_special(root)
    
    def _extract_depreciation(self, root: ET.Element) -> Optional[float]:
        """Extract depreciation expenses"""
        return self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['depreciation'])
    
    def _extract_market_cap(self, root: ET.Element) -> Optional[float]:
        """Extract market capitalization"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['market_cap'])
    
    def _extract_per(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-earnings ratio"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['per'])
    
    def _extract_pbr(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-book ratio"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['pbr'])
    
    def _extract_equity(self, root: ET.Element) -> Optional[float]:
        """Extract total equity/shareholders' equity"""
        return self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['equity'])
    
    def _extract_debt(self, root: ET.Element) -> Optional[float]:
        """Extract net interest-bearing debt"""
        return self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['debt'])
    
    def _extract_outstanding_shares(self, root: ET.Element) -> Optional[int]:
        """Extract outstanding shares (actually issued shares)"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['outstanding_shares'])
        if value is not None:
            return int(value)
        
        # Fallback: Dynamic search for share-related tags
        value = self._dynamic_search_shares(root)
        return int(value) if value is not None else None
    
    def _dynamic_search_shares(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for share-related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Share count value or None
        """
        share_candidates = []
        
        # Keywords indicating share-related data
        share_keywords = [
            'NumberOfShares', 'SharesIssued', 'SharesOutstanding', 'IssuedShares',
            'NumberOfIssuedShares', 'NumberOfOutstandingShares', 'TotalShares',
            'CommonShares', 'CapitalStock', 'StockShares'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains share-related keywords
                for keyword in share_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable share counts (between 1,000 and 100 billion)
                            if 1_000 <= numeric_value <= 100_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                priority = self._calculate_share_priority(local_name, context_ref, numeric_value)
                                share_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if share_candidates:
            share_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = share_candidates[0]
            print(f"Dynamic share search found: {best_match[0]:,.0f} shares from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_share_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for share candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for current year context
        if 'CurrentYear' in context_ref:
            priority += 20
        elif 'Current' in context_ref:
            priority += 15
        
        # Higher priority for "outstanding" or "issued"
        if 'outstanding' in tag_name.lower():
            priority += 15
        elif 'issued' in tag_name.lower():
            priority += 12
        
        # Higher priority for end-of-period data
        if any(term in tag_name.lower() for term in ['attheendof', 'endof', 'fiscal', 'year']):
            priority += 10
        
        # Higher priority for common stock
        if 'common' in tag_name.lower():
            priority += 8
        
        # Prefer values in typical ranges for Japanese companies
        if 10_000_000 <= value <= 10_000_000_000:  # 10M to 10B shares
            priority += 5
        elif 1_000_000 <= value <= 100_000_000_000:  # 1M to 100B shares
            priority += 3
        
        # Lower priority for treasury stock or authorized shares
        if any(term in tag_name.lower() for term in ['treasury', 'authorized']):
            priority -= 5
        
        return priority