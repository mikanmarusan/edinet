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
        Extract numeric value with priority for consolidated current year context
        
        Args:
            root: XBRL root element
            patterns: List of XPath patterns to try
            
        Returns:
            Extracted numeric value or None
        """
        for pattern in patterns:
            elements = root.findall(pattern, self.namespaces)
            if elements:
                # Separate elements by priority, excluding NonConsolidatedMember
                consolidated_current_elements = []
                current_year_elements = []
                consolidated_elements = []
                other_elements = []
                
                for element in elements:
                    context_ref = element.get('contextRef', '')
                    
                    # Skip NonConsolidatedMember contexts (individual company data)
                    if 'NonConsolidatedMember' in context_ref:
                        continue
                    
                    # Prioritize consolidated data
                    if 'Consolidated' in context_ref and 'CurrentYear' in context_ref:
                        consolidated_current_elements.append(element)
                    elif 'CurrentYear' in context_ref:
                        current_year_elements.append(element)
                    elif 'Consolidated' in context_ref:
                        consolidated_elements.append(element)
                    else:
                        other_elements.append(element)
                
                # Try consolidated current year elements first (highest priority)
                for element in consolidated_current_elements:
                    if element.text:
                        try:
                            return float(element.text.replace(',', ''))
                        except ValueError:
                            continue
                
                # Try current year elements
                for element in current_year_elements:
                    if element.text:
                        try:
                            return float(element.text.replace(',', ''))
                        except ValueError:
                            continue
                
                # Try consolidated elements
                for element in consolidated_elements:
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
        Extract text value from XBRL with HTML sanitization
        
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
                # Remove HTML tags and entities
                text = self._sanitize_html_text(text)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                return text[:max_length] + "..." if len(text) > max_length else text
        return None
    
    def _sanitize_html_text(self, text: str) -> str:
        """
        Remove HTML tags and decode HTML entities from text
        
        Args:
            text: Text that may contain HTML tags
            
        Returns:
            Cleaned text with HTML tags removed
        """
        if not text:
            return ""
        
        # Remove HTML/XML tags using regex
        # Remove all tags like <tag>, <tag attr="value">, </tag>, <tag/>
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&nbsp;': ' ',
            '&#x20;': ' ',
            '&#32;': ' ',
            '&#160;': ' ',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™'
        }
        
        for entity, replacement in html_entities.items():
            clean_text = clean_text.replace(entity, replacement)
        
        # Remove any remaining HTML entities (&#number; or &#xhex;)
        clean_text = re.sub(r'&#?\w+;', '', clean_text)
        
        # Clean up multiple whitespace characters
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
    
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
            # Separate elements by priority: Consolidated CurrentYear > CurrentYear > Consolidated > Others
            consolidated_current_elements = []
            current_year_elements = []
            consolidated_elements = []
            other_elements = []
            
            for element in operating_income_elements:
                context_ref = element.get('contextRef', '')
                
                # Skip NonConsolidatedMember contexts (individual company data)
                if 'NonConsolidatedMember' in context_ref:
                    continue
                
                if 'Consolidated' in context_ref and 'CurrentYear' in context_ref:
                    consolidated_current_elements.append(element)
                elif 'CurrentYear' in context_ref:
                    current_year_elements.append(element)
                elif 'Consolidated' in context_ref:
                    consolidated_elements.append(element)
                else:
                    other_elements.append(element)
            
            # Try consolidated current year elements first (highest priority)
            for element in consolidated_current_elements:
                if element.text:
                    try:
                        return float(element.text.replace(',', ''))
                    except ValueError:
                        continue
            
            # Try current year elements
            for element in current_year_elements:
                if element.text:
                    try:
                        return float(element.text.replace(',', ''))
                    except ValueError:
                        continue
            
            # Try consolidated elements
            for element in consolidated_elements:
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
            outstanding_shares = financial_data.get('outstandingShares')
            stock_price = financial_data.get('stockPrice')
            
            # Operating income rate
            if net_sales and operating_income and net_sales > 0:
                financial_data['operatingIncomeRate'] = (operating_income / net_sales) * 100
            
            # EBITDA
            if operating_income and depreciation:
                financial_data['ebitda'] = operating_income + depreciation
            
            # EBITDA margin
            if financial_data.get('ebitda') and net_sales and net_sales > 0:
                financial_data['ebitdaMargin'] = (financial_data['ebitda'] / net_sales) * 100
            
            # Calculate missing financial metrics (Issue #21)
            # stockPrice = eps × per (only if stockPrice is missing)
            if not financial_data.get('stockPrice'):
                eps = financial_data.get('eps')
                per = financial_data.get('per')
                if eps is not None and per is not None:
                    financial_data['stockPrice'] = eps * per
                else:
                    financial_data['stockPrice'] = None
            
            # marketCapitalization = outstandingShares × stockPrice (only if marketCapitalization is missing)
            if not financial_data.get('marketCapitalization'):
                outstanding_shares = financial_data.get('outstandingShares')
                calculated_stock_price = financial_data.get('stockPrice')
                if outstanding_shares is not None and calculated_stock_price is not None:
                    financial_data['marketCapitalization'] = outstanding_shares * calculated_stock_price
                else:
                    financial_data['marketCapitalization'] = None
            
            # pbr = stockPrice ÷ bps (only if pbr is missing)
            if not financial_data.get('pbr'):
                calculated_stock_price = financial_data.get('stockPrice')
                bps = financial_data.get('bps')
                if calculated_stock_price is not None and bps is not None and bps > 0:
                    financial_data['pbr'] = calculated_stock_price / bps
                else:
                    financial_data['pbr'] = None
            
            # Enterprise Value (EV) = marketCapitalization + debt - cash
            calculated_market_cap = financial_data.get('marketCapitalization')
            debt = financial_data.get('debt')
            cash = financial_data.get('cash')
            if calculated_market_cap is not None and debt is not None and cash is not None:
                financial_data['ev'] = calculated_market_cap + debt - cash
            else:
                financial_data['ev'] = None
            
            # EV/EBITDA
            if financial_data.get('ev') and financial_data.get('ebitda') and financial_data['ebitda'] > 0:
                financial_data['evPerEbitda'] = financial_data['ev'] / financial_data['ebitda']
            else:
                financial_data['evPerEbitda'] = None
            
            # Calculate EPS if not already available and we have the necessary data
            if not financial_data.get('eps'):
                calculated_eps = MetricsCalculator._calculate_eps(financial_data)
                if calculated_eps is not None:
                    financial_data['eps'] = calculated_eps
                    print(f"Calculated EPS: {calculated_eps:.2f} yen")
            
            # Calculate PER if not already available and we have the necessary data
            if not financial_data.get('per'):
                calculated_per = MetricsCalculator._calculate_per(financial_data)
                if calculated_per is not None:
                    financial_data['per'] = calculated_per
                    print(f"Calculated PER: {calculated_per:.2f}")
            
            # Calculate BPS if not already available and we have the necessary data
            if not financial_data.get('bps'):
                calculated_bps = MetricsCalculator._calculate_bps(financial_data)
                if calculated_bps is not None:
                    financial_data['bps'] = calculated_bps
                    print(f"Calculated BPS: {calculated_bps:.2f} yen")
            
        except Exception as e:
            print(f"Error calculating derived metrics: {e}", file=sys.stderr)
        
        return financial_data
    
    @staticmethod
    def _calculate_eps(financial_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate EPS from net income and outstanding shares
        
        Args:
            financial_data: Dictionary with financial data
            
        Returns:
            Calculated EPS or None
        """
        try:
            # Priority 1: Use actual net income if available
            net_income = financial_data.get('netIncome')
            outstanding_shares = financial_data.get('outstandingShares')
            
            if net_income and outstanding_shares and outstanding_shares > 0:
                eps = net_income / outstanding_shares
                return eps
            
            # Priority 2: Use operating income as approximation
            operating_income = financial_data.get('operatingIncome')
            if operating_income and outstanding_shares and outstanding_shares > 0:
                # This is an approximation - operating income is typically higher than net income
                # We apply a rough adjustment factor of 0.7 to approximate net income
                estimated_net_income = operating_income * 0.7
                eps = estimated_net_income / outstanding_shares
                return eps
            
        except Exception as e:
            print(f"Error calculating EPS: {e}", file=sys.stderr)
        
        return None
    
    @staticmethod
    def _calculate_per(financial_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate PER from stock price and EPS
        
        Args:
            financial_data: Dictionary with financial data
            
        Returns:
            Calculated PER or None
        """
        try:
            stock_price = financial_data.get('stockPrice')
            eps = financial_data.get('eps')
            
            if stock_price and eps and eps > 0:
                per = stock_price / eps
                return per
            
        except Exception as e:
            print(f"Error calculating PER: {e}", file=sys.stderr)
        
        return None
    
    @staticmethod
    def _calculate_bps(financial_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate BPS (Book Value Per Share) from equity and outstanding shares
        
        Args:
            financial_data: Dictionary with financial data
            
        Returns:
            Calculated BPS or None
        """
        try:
            equity = financial_data.get('equity')
            outstanding_shares = financial_data.get('outstandingShares')
            
            if equity and outstanding_shares and outstanding_shares > 0:
                bps = equity / outstanding_shares
                return bps
            
        except Exception as e:
            print(f"Error calculating BPS: {e}", file=sys.stderr)
        
        return None


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
            "bps": self._extract_bps(root),
            "equity": self._extract_equity(root),
            "debt": self._extract_debt(root),
            "outstandingShares": self._extract_outstanding_shares(root),
            "netIncome": self._extract_net_income(root),
            "eps": self._extract_eps(root),
            "cash": self._extract_cash(root),
            "retrievedDate": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _extract_characteristic(self, root: ET.Element) -> Optional[str]:
        """Extract first sentence of company characteristics/business description"""
        # Try standard patterns first
        full_text = self.data_extractor.extract_text_value(root, self.data_extractor.patterns['characteristic'], max_length=1000)
        if full_text:
            # Extract first sentence
            return self._extract_first_sentence(full_text)
        
        # Fallback: Dynamic search for business description
        full_text = self._dynamic_search_business_description(root)
        if full_text:
            return self._extract_first_sentence(full_text)
        
        return None
    
    def _extract_stock_price(self, root: ET.Element) -> Optional[float]:
        """Extract stock price"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['stock_price'])
    
    def _extract_net_sales(self, root: ET.Element) -> Optional[float]:
        """Extract net sales/revenue with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['net_sales'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for sales-related tags
        return self._dynamic_search_net_sales(root)
    
    def _extract_employees(self, root: ET.Element) -> Optional[int]:
        """Extract number of employees with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['employees'])
        if value is not None:
            return int(value)
        
        # Fallback: Dynamic search for employee-related tags
        value = self._dynamic_search_employees(root)
        return int(value) if value is not None else None
    
    def _extract_operating_income(self, root: ET.Element) -> Optional[float]:
        """Extract operating income"""
        return self.data_extractor.extract_operating_income_special(root)
    
    def _extract_depreciation(self, root: ET.Element) -> Optional[float]:
        """Extract depreciation expenses with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['depreciation'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for depreciation-related tags
        return self._dynamic_search_depreciation(root)
    
    def _extract_market_cap(self, root: ET.Element) -> Optional[float]:
        """Extract market capitalization"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['market_cap'])
    
    def _extract_per(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-earnings ratio"""
        # Try standard patterns first
        per_value = self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['per'])
        if per_value is not None:
            return per_value
        
        # Dynamic search for PER-related tags
        return self._dynamic_search_per(root)
    
    def _dynamic_search_per(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for PER-related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            PER value or None
        """
        per_candidates = []
        
        # Keywords indicating PER-related data
        per_keywords = [
            'PriceEarningsRatio', 'PriceToEarnings', 'PER', 'PE', 'PEMultiple',
            'PriceEarnings', 'StockPriceEarningsRatio', 'SharePriceEarningsRatio'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains PER-related keywords
                for keyword in per_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable PER values (between 0 and 1000)
                            if 0 <= numeric_value <= 1000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_per_priority(local_name, context_ref, numeric_value)
                                per_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if per_candidates:
            per_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = per_candidates[0]
            print(f"Dynamic PER search found: {best_match[0]:.2f} from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_per_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for PER candidate
        
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
        
        # Higher priority for exact PER tags
        if tag_name.lower() in ['per', 'priceearningsratio', 'pricetoearnings']:
            priority += 15
        
        # Higher priority for price-earnings combinations
        if 'price' in tag_name.lower() and 'earnings' in tag_name.lower():
            priority += 12
        
        # Prefer reasonable PER values (typical range for listed companies)
        if 5 <= value <= 50:  # Most reasonable PER range
            priority += 10
        elif 1 <= value <= 100:
            priority += 5
        elif 0 < value <= 200:
            priority += 2
        
        return priority
    
    def _extract_pbr(self, root: ET.Element) -> Optional[float]:
        """Extract price-to-book ratio"""
        return self.data_extractor.extract_numeric_value(root, self.data_extractor.patterns['pbr'])
    
    def _extract_bps(self, root: ET.Element) -> Optional[float]:
        """Extract book value per share (BPS) with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['bps'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for BPS-related tags
        return self._dynamic_search_bps(root)
    
    def _extract_equity(self, root: ET.Element) -> Optional[float]:
        """Extract total equity/shareholders' equity with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['equity'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for equity-related tags
        return self._dynamic_search_equity(root)
    
    def _extract_debt(self, root: ET.Element) -> Optional[float]:
        """Extract net interest-bearing debt with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['debt'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for debt-related tags
        dynamic_value = self._dynamic_search_debt(root)
        if dynamic_value is not None:
            return dynamic_value
        
        # Final fallback: Try to calculate debt from short-term + long-term components
        return self._calculate_debt_from_components(root)
    
    def _extract_net_income(self, root: ET.Element) -> Optional[float]:
        """Extract net income with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['net_income'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for net income-related tags
        return self._dynamic_search_net_income(root)
    
    def _extract_cash(self, root: ET.Element) -> Optional[float]:
        """Extract cash and cash equivalents with enhanced pattern matching"""
        # Try standard patterns first
        value = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['cash'])
        if value is not None:
            return value
        
        # Fallback: Dynamic search for cash-related tags
        return self._dynamic_search_cash(root)
    
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
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
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
    
    def _dynamic_search_net_sales(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for net sales/revenue related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Net sales value or None
        """
        sales_candidates = []
        
        # Keywords indicating sales/revenue-related data
        sales_keywords = [
            'NetSales', 'Revenue', 'Sales', 'TotalRevenue', 'OperatingRevenue',
            'TotalSales', 'TotalNetSales', 'ConsolidatedNetSales', 'ConsolidatedRevenue'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains sales-related keywords
                for keyword in sales_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable sales values (between 1M and 100T yen)
                            if 1_000_000 <= numeric_value <= 100_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_sales_priority(local_name, context_ref, numeric_value)
                                sales_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if sales_candidates:
            sales_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = sales_candidates[0]
            print(f"Dynamic net sales search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_sales_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for sales candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact sales/revenue tags
        if any(term in tag_name.lower() for term in ['netsales', 'revenue', 'totalrevenue']):
            priority += 15
        elif 'sales' in tag_name.lower():
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Prefer reasonable sales values for Japanese companies
        if 100_000_000 <= value <= 10_000_000_000_000:  # 100M to 10T yen
            priority += 10
        elif 10_000_000 <= value <= 100_000_000_000_000:  # 10M to 100T yen
            priority += 5
        
        return priority
    
    def _dynamic_search_employees(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for employee count related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Employee count value or None
        """
        employee_candidates = []
        
        # Keywords indicating employee-related data
        employee_keywords = [
            'NumberOfEmployees', 'Employees', 'TotalEmployees', 'EmployeeCount',
            'ConsolidatedNumberOfEmployees', 'ConsolidatedEmployees', 'Staff',
            'Personnel', 'WorkForce', 'TotalPersonnel'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains employee-related keywords
                for keyword in employee_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable employee counts (between 1 and 1M employees)
                            if 1 <= numeric_value <= 1_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_employee_priority(local_name, context_ref, numeric_value)
                                employee_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if employee_candidates:
            employee_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = employee_candidates[0]
            print(f"Dynamic employee search found: {best_match[0]:,.0f} employees from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_employee_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for employee candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact employee tags
        if 'numberofemployees' in tag_name.lower():
            priority += 15
        elif 'employees' in tag_name.lower():
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Prefer reasonable employee counts for Japanese companies
        if 10 <= value <= 100_000:  # 10 to 100K employees (typical range)
            priority += 10
        elif 1 <= value <= 500_000:  # 1 to 500K employees
            priority += 5
        
        return priority
    
    def _dynamic_search_equity(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for equity/shareholders' equity related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Equity value or None
        """
        equity_candidates = []
        
        # Keywords indicating equity-related data
        equity_keywords = [
            'ShareholdersEquity', 'Equity', 'NetAssets', 'TotalEquity', 'OwnersEquity',
            'ConsolidatedEquity', 'ConsolidatedShareholdersEquity', 'NetWorth',
            'ShareholdersCapital', 'StockholdersEquity', 'TotalNetAssets',
            'EquityAttributableToOwnersOfParent', 'ParentCompanyShareholdersEquity'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains equity-related keywords
                for keyword in equity_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable equity values (between 100M and 100T yen)
                            if 100_000_000 <= numeric_value <= 100_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_equity_priority(local_name, context_ref, numeric_value)
                                equity_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if equity_candidates:
            equity_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = equity_candidates[0]
            print(f"Dynamic equity search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_equity_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for equity candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact equity tags
        if any(term in tag_name.lower() for term in ['shareholdersequity', 'equity', 'netassets']):
            priority += 15
        elif 'equity' in tag_name.lower():
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Higher priority for parent company equity
        if any(term in tag_name.lower() for term in ['parent', 'owners', 'attributable']):
            priority += 8
        
        # Prefer reasonable equity values for Japanese companies
        if 1_000_000_000 <= value <= 10_000_000_000_000:  # 1B to 10T yen
            priority += 10
        elif 100_000_000 <= value <= 100_000_000_000_000:  # 100M to 100T yen
            priority += 5
        
        return priority
    
    def _dynamic_search_depreciation(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for depreciation and amortization related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Depreciation value or None
        """
        depreciation_candidates = []
        
        # Keywords indicating depreciation-related data
        depreciation_keywords = [
            'DepreciationAndAmortization', 'Depreciation', 'Amortization', 'DepreciationExpenses',
            'ConsolidatedDepreciation', 'ConsolidatedDepreciationAndAmortization', 
            'DepreciationAndAmortizationExpenses', 'DepreciationCosts', 'AmortizationExpenses',
            'TangibleAssetsDepreciation', 'IntangibleAssetsAmortization', 'DepreciationOfProperty'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains depreciation-related keywords
                for keyword in depreciation_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable depreciation values (between 10M and 1T yen)
                            if 10_000_000 <= numeric_value <= 1_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_depreciation_priority(local_name, context_ref, numeric_value)
                                depreciation_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if depreciation_candidates:
            depreciation_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = depreciation_candidates[0]
            print(f"Dynamic depreciation search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_depreciation_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for depreciation candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact depreciation tags
        if any(term in tag_name.lower() for term in ['depreciationandamortization', 'depreciation']):
            priority += 15
        elif 'depreciation' in tag_name.lower() or 'amortization' in tag_name.lower():
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Higher priority for expenses/costs
        if any(term in tag_name.lower() for term in ['expenses', 'costs', 'expense']):
            priority += 8
        
        # Higher priority for cash flow related depreciation
        if any(term in tag_name.lower() for term in ['cashflow', 'cf', 'operatingcf']):
            priority += 12
        
        # Prefer reasonable depreciation values for Japanese companies
        if 100_000_000 <= value <= 100_000_000_000:  # 100M to 100B yen
            priority += 10
        elif 10_000_000 <= value <= 1_000_000_000_000:  # 10M to 1T yen
            priority += 5
        
        return priority
    
    def _dynamic_search_net_income(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for net income related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Net income value or None
        """
        net_income_candidates = []
        
        # Keywords indicating net income-related data
        net_income_keywords = [
            'NetIncome', 'NetIncomeLoss', 'ProfitLoss', 'Profit', 'NetProfit',
            'ConsolidatedNetIncome', 'ConsolidatedNetIncomeLoss', 'ConsolidatedProfit',
            'NetIncomeAttributableToOwnersOfParent', 'NetIncomeAttributableToParent',
            'ParentCompanyNetIncome', 'BasicNetIncome', 'NetIncomeCommon',
            'ProfitAttributableToOwnersOfParent', 'NetIncomeBeforeExtraordinaryItems'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains net income-related keywords
                for keyword in net_income_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable net income values (between -1T and 1T yen, allowing losses)
                            if -1_000_000_000_000 <= numeric_value <= 1_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_net_income_priority(local_name, context_ref, numeric_value)
                                net_income_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if net_income_candidates:
            net_income_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = net_income_candidates[0]
            print(f"Dynamic net income search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_net_income_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for net income candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact net income tags
        if any(term in tag_name.lower() for term in ['netincome', 'netincomeloss', 'profitloss']):
            priority += 15
        elif any(term in tag_name.lower() for term in ['profit', 'income']):
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Higher priority for parent company attributable income
        if any(term in tag_name.lower() for term in ['attributable', 'parent', 'owners']):
            priority += 12
        
        # Higher priority for summary/results sections
        if any(term in tag_name.lower() for term in ['summary', 'results']):
            priority += 8
        
        # Prefer reasonable net income values for Japanese companies
        if abs(value) >= 100_000_000:  # At least 100M yen (absolute value for losses)
            if abs(value) <= 100_000_000_000:  # Up to 100B yen
                priority += 10
            elif abs(value) <= 1_000_000_000_000:  # Up to 1T yen
                priority += 5
        
        return priority
    
    def _extract_eps(self, root: ET.Element) -> Optional[float]:
        """Extract earnings per share, preferring diluted over basic"""
        # Try diluted EPS first (priority)
        diluted_eps = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['eps_diluted'])
        if diluted_eps is not None:
            return diluted_eps
        
        # Fallback to basic EPS
        basic_eps = self.data_extractor.extract_numeric_value_with_context(root, self.data_extractor.patterns['eps_basic'])
        if basic_eps is not None:
            return basic_eps
        
        # Dynamic search for EPS-related tags
        return self._dynamic_search_eps(root)
    
    def _dynamic_search_eps(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for EPS-related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            EPS value or None
        """
        eps_candidates = []
        
        # Keywords indicating EPS-related data
        eps_keywords = [
            'EarningsPerShare', 'NetIncomePerShare', 'BasicEarnings', 'DilutedEarnings',
            'ProfitPerShare', 'IncomePerShare', 'EarningsAttributable',
            'BasicNetIncomePerShare', 'DilutedNetIncomePerShare'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains EPS-related keywords
                for keyword in eps_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable EPS values (between -10,000 and 10,000 yen)
                            if -10_000 <= numeric_value <= 10_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_eps_priority(local_name, context_ref, numeric_value)
                                eps_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if eps_candidates:
            eps_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = eps_candidates[0]
            print(f"Dynamic EPS search found: {best_match[0]:.2f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_eps_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for EPS candidate
        
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
        
        # Higher priority for diluted EPS
        if 'diluted' in tag_name.lower():
            priority += 15
        elif 'basic' in tag_name.lower():
            priority += 12
        
        # Higher priority for "per share" tags
        if 'pershare' in tag_name.lower():
            priority += 10
        
        # Higher priority for earnings/income
        if any(term in tag_name.lower() for term in ['earnings', 'income', 'profit']):
            priority += 8
        
        # Prefer reasonable EPS values (not too extreme)
        if 0 <= abs(value) <= 1000:  # Most Japanese company EPS is in this range
            priority += 5
        elif 0 <= abs(value) <= 5000:
            priority += 3
        
        return priority
    
    def _dynamic_search_bps(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for BPS (Book Value Per Share) related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            BPS value or None
        """
        bps_candidates = []
        
        # Keywords indicating BPS-related data
        bps_keywords = [
            'BookValuePerShare', 'NetAssetsPerShare', 'NetBookValuePerShare',
            'ShareholdersEquityPerShare', 'BookValue', 'NetAssets',
            'ConsolidatedBookValuePerShare', 'ConsolidatedNetAssetsPerShare',
            'BookValuePerCommonShare', 'NetAssetsPerCommonShare',
            'EquityPerShare', 'NetWorthPerShare'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains BPS-related keywords
                for keyword in bps_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable BPS values (between 1 and 100,000 yen per share)
                            if 1 <= numeric_value <= 100_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_bps_priority(local_name, context_ref, numeric_value)
                                bps_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if bps_candidates:
            bps_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = bps_candidates[0]
            print(f"Dynamic BPS search found: {best_match[0]:.2f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_bps_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for BPS candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for exact BPS tags
        if any(term in tag_name.lower() for term in ['bookvaluepershare', 'netassetspershare']):
            priority += 15
        elif any(term in tag_name.lower() for term in ['bookvalue', 'netassets', 'equity']):
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Higher priority for per share indicators
        if 'pershare' in tag_name.lower():
            priority += 10
        elif 'share' in tag_name.lower():
            priority += 8
        
        # Prefer reasonable BPS values for Japanese companies
        if 100 <= value <= 10_000:  # 100 to 10,000 yen per share (typical range)
            priority += 10
        elif 10 <= value <= 50_000:  # 10 to 50,000 yen per share
            priority += 5
        elif 1 <= value <= 100_000:  # 1 to 100,000 yen per share
            priority += 3
        
        return priority
    
    def _dynamic_search_debt(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for debt (interest-bearing debt) related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Debt value or None
        """
        debt_candidates = []
        
        # Keywords indicating debt-related data
        debt_keywords = [
            # Primary debt terms
            'InterestBearingDebt', 'TotalInterestBearingDebt', 'NetInterestBearingDebt',
            'TotalDebt', 'NetDebt', 'Debt', 'BorrowingsAndDebt',
            
            # Consolidated debt terms
            'ConsolidatedInterestBearingDebt', 'ConsolidatedTotalInterestBearingDebt',
            'ConsolidatedDebt', 'ConsolidatedTotalDebt', 'ConsolidatedNetDebt',
            'ConsolidatedBorrowings', 'ConsolidatedTotalBorrowings',
            
            # Borrowings terms
            'Borrowings', 'TotalBorrowings', 'NetBorrowings', 'BorrowingsAndDebt',
            'ShortTermBorrowings', 'LongTermBorrowings',
            
            # Loans terms
            'Loans', 'TotalLoans', 'LoanPayable', 'LoansPayable',
            'ShortTermLoans', 'LongTermLoans', 'BankLoans',
            
            # Debt classification terms
            'ShortTermDebt', 'LongTermDebt', 'CurrentDebt', 'NonCurrentDebt',
            
            # Specific debt instruments
            'BondsPayable', 'CorporateBonds', 'NotesPayable', 'BillsPayable',
            'Debentures', 'ConvertibleBonds',
            
            # Liabilities terms
            'InterestBearingLiabilities', 'FinancialLiabilities', 'DebtLiabilities',
            
            # IFRS terms
            'FinancialLiabilitiesIFRS', 'ConsolidatedFinancialLiabilities',
            'ConsolidatedFinancialLiabilitiesIFRS',
            
            # Other debt-related terms
            'DebtFinancing', 'InterestPayable', 'AccruedInterest',
            'CommercialPaper', 'CreditFacilities', 'LineOfCredit',
            
            # Japanese-specific terms (romanized)
            'Shakkan', 'Fusai', 'Kariire', 'Shakkankin', 'Fusaikin'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains debt-related keywords
                for keyword in debt_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable debt values (between 0 and 100T yen, including 0 for debt-free companies)
                            if 0 <= numeric_value <= 100_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_debt_priority(local_name, context_ref, numeric_value)
                                debt_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if debt_candidates:
            debt_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = debt_candidates[0]
            print(f"Dynamic debt search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_debt_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for debt candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Highest priority for interest-bearing debt (most accurate for financial analysis)
        if any(term in tag_name.lower() for term in ['interestbearingdebt', 'totalinterestbearingdebt', 'netinterestbearingdebt']):
            priority += 20
        elif any(term in tag_name.lower() for term in ['totaldebt', 'netdebt']):
            priority += 18
        elif any(term in tag_name.lower() for term in ['totalborrowing', 'netborrowing']):
            priority += 16
        elif any(term in tag_name.lower() for term in ['debt', 'borrowings', 'loans']):
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 12
        
        # Higher priority for total vs specific components
        if 'total' in tag_name.lower():
            priority += 10
        elif 'net' in tag_name.lower():
            priority += 8  # Net debt is preferred over gross debt
        
        # Boost priority for financial liabilities (IFRS)
        if any(term in tag_name.lower() for term in ['financialliabilities', 'financialliabilitiesifrs']):
            priority += 15
        
        # Higher priority for comprehensive debt terms
        if any(term in tag_name.lower() for term in ['borrowingsanddebt', 'debtandborrowings']):
            priority += 14
        
        # Lower priority for specific short-term components unless it's a comprehensive measure
        if any(term in tag_name.lower() for term in ['shortterm', 'current']) and 'total' not in tag_name.lower():
            priority -= 5
        
        # Higher priority for current year/fiscal year context
        if any(term in context_ref.lower() for term in ['currentyear', 'current', 'fiscal']):
            priority += 8
        
        # Prefer reasonable debt values for Japanese companies
        if 100_000_000 <= value <= 50_000_000_000_000:  # 100M to 50T yen (reasonable range)
            priority += 12
        elif 10_000_000 <= value <= 100_000_000_000_000:  # 10M to 100T yen
            priority += 8
        elif 0 <= value <= 10_000_000:  # Very small debt (could be debt-free)
            priority += 5
        
        # Slight penalty for extremely large values that might be errors
        if value > 100_000_000_000_000:  # Over 100T yen
            priority -= 5
        
        return priority
    
    def _calculate_debt_from_components(self, root: ET.Element) -> Optional[float]:
        """
        Calculate total debt from short-term and long-term debt components
        
        Args:
            root: XBRL root element
            
        Returns:
            Calculated total debt or None
        """
        short_term_debt = None
        long_term_debt = None
        
        # Patterns for short-term debt
        short_term_patterns = [
            './/jpcrp_cor:ShortTermBorrowings',
            './/jppfs_cor:ShortTermBorrowings',
            './/jpcrp_cor:ShortTermDebt',
            './/jppfs_cor:ShortTermDebt',
            './/jpcrp_cor:ShortTermLoans',
            './/jppfs_cor:ShortTermLoans',
            './/jpcrp_cor:CurrentPortionOfLongTermDebt',
            './/jppfs_cor:CurrentPortionOfLongTermDebt',
            './/jpcrp_cor:ConsolidatedShortTermBorrowings',
            './/jppfs_cor:ConsolidatedShortTermBorrowings'
        ]
        
        # Patterns for long-term debt
        long_term_patterns = [
            './/jpcrp_cor:LongTermBorrowings',
            './/jppfs_cor:LongTermBorrowings',
            './/jpcrp_cor:LongTermDebt',
            './/jppfs_cor:LongTermDebt',
            './/jpcrp_cor:LongTermLoans',
            './/jppfs_cor:LongTermLoans',
            './/jpcrp_cor:ConsolidatedLongTermBorrowings',
            './/jppfs_cor:ConsolidatedLongTermBorrowings',
            './/jpcrp_cor:BondsPayable',
            './/jppfs_cor:BondsPayable'
        ]
        
        # Try to extract short-term debt
        short_term_debt = self.data_extractor.extract_numeric_value_with_context(root, short_term_patterns)
        
        # Try to extract long-term debt
        long_term_debt = self.data_extractor.extract_numeric_value_with_context(root, long_term_patterns)
        
        # Calculate total if we have at least one component
        if short_term_debt is not None and long_term_debt is not None:
            total_debt = short_term_debt + long_term_debt
            print(f"Calculated total debt from components: {short_term_debt:,.0f} (short-term) + {long_term_debt:,.0f} (long-term) = {total_debt:,.0f}")
            return total_debt
        elif short_term_debt is not None:
            print(f"Using short-term debt only: {short_term_debt:,.0f}")
            return short_term_debt
        elif long_term_debt is not None:
            print(f"Using long-term debt only: {long_term_debt:,.0f}")
            return long_term_debt
        
        return None
    
    def _dynamic_search_cash(self, root: ET.Element) -> Optional[float]:
        """
        Dynamic search for cash and cash equivalents related tags when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Cash value or None
        """
        cash_candidates = []
        
        # Keywords indicating cash and cash equivalents-related data
        cash_keywords = [
            'CashAndCashEquivalents', 'CashAndEquivalents', 'CashAndDeposits',
            'ConsolidatedCashAndCashEquivalents', 'CashEquivalents', 'Cash',
            'CashAndCashEquivalentsAtEndOfPeriod', 'CashAndCashEquivalentsAtEndOfFiscalYear',
            'CashAndCashEquivalentsBalanceAtEndOfPeriod', 'CashBalance',
            'CashDepositsAndShortTermInvestments', 'CashAndShortTermInvestments',
            'MoneyAndDeposits', 'CashOnHand', 'CashInBank'
        ]
        
        # Search through all elements
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains cash-related keywords
                for keyword in cash_keywords:
                    if keyword.lower() in local_name.lower():
                        try:
                            # Try to parse as number
                            value_text = elem.text.replace(',', '').strip()
                            numeric_value = float(value_text)
                            
                            # Filter reasonable cash values (between 1M and 10T yen)
                            if 1_000_000 <= numeric_value <= 10_000_000_000_000:
                                context_ref = elem.get('contextRef', '')
                                
                                # Skip NonConsolidatedMember contexts (individual company data)
                                if 'NonConsolidatedMember' in context_ref:
                                    continue
                                
                                priority = self._calculate_cash_priority(local_name, context_ref, numeric_value)
                                cash_candidates.append((numeric_value, priority, local_name, context_ref))
                                
                        except (ValueError, AttributeError):
                            continue
                        break
        
        # Sort by priority (higher is better) and return the best match
        if cash_candidates:
            cash_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = cash_candidates[0]
            print(f"Dynamic cash search found: {best_match[0]:,.0f} yen from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_cash_priority(self, tag_name: str, context_ref: str, value: float) -> int:
        """
        Calculate priority score for cash candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            value: Numeric value
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for consolidated data
        if 'Consolidated' in context_ref:
            priority += 25
            if 'CurrentYear' in context_ref:
                priority += 20  # Consolidated + CurrentYear is highest priority
        elif 'CurrentYear' in context_ref:
            priority += 15
        
        # Higher priority for end-of-period data
        if any(term in context_ref.lower() for term in ['endofperiod', 'endoffiscalyear', 'end']):
            priority += 15
        
        # Higher priority for exact cash and cash equivalents tags
        if any(term in tag_name.lower() for term in ['cashandcashequivalents', 'cashequivalents']):
            priority += 15
        elif any(term in tag_name.lower() for term in ['cash', 'deposits']):
            priority += 12
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 10
        
        # Higher priority for balance/end-of-period in tag name
        if any(term in tag_name.lower() for term in ['balance', 'endofperiod', 'endoffiscalyear']):
            priority += 8
        
        # Prefer reasonable cash values for Japanese companies
        if 1_000_000_000 <= value <= 1_000_000_000_000:  # 1B to 1T yen
            priority += 10
        elif 100_000_000 <= value <= 10_000_000_000_000:  # 100M to 10T yen
            priority += 5
        
        return priority
    
    def _extract_first_sentence(self, text: str) -> str:
        """
        Extract the first sentence from text
        
        Args:
            text: Full text to extract sentence from
            
        Returns:
            First sentence of the text
        """
        if not text:
            return ""
        
        # Clean up the text
        text = text.strip()
        
        # Look for sentence-ending punctuation: 。、！？.!?
        # Japanese text typically uses 。 as sentence ending
        sentence_endings = ['。', '！', '？', '.', '!', '?']
        
        # Find the first sentence ending
        first_ending_pos = len(text)  # Default to full text if no ending found
        
        for ending in sentence_endings:
            pos = text.find(ending)
            if pos != -1 and pos < first_ending_pos:
                first_ending_pos = pos
        
        # Extract first sentence including the punctuation
        if first_ending_pos < len(text):
            first_sentence = text[:first_ending_pos + 1].strip()
        else:
            # No sentence ending found, take first 100 characters and add ...
            first_sentence = text[:100].strip()
            if len(text) > 100:
                first_sentence += "..."
        
        return first_sentence
    
    def _sanitize_html(self, text: str) -> str:
        """
        Remove HTML tags and decode HTML entities from text
        
        Args:
            text: Text that may contain HTML tags
            
        Returns:
            Cleaned text with HTML tags removed
        """
        if not text:
            return ""
        
        import re
        
        # Remove dangerous script and style tags along with their content
        clean_text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove all HTML/XML tags like <tag>, <tag attr="value">, </tag>, <tag/>
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # Decode common HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&nbsp;': ' ',
            '&#x20;': ' ',
            '&#32;': ' ',
            '&#160;': ' ',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™'
        }
        
        for entity, replacement in html_entities.items():
            clean_text = clean_text.replace(entity, replacement)
        
        # Remove any remaining HTML entities (&#number; or &#xhex;)
        clean_text = re.sub(r'&#?\w+;', '', clean_text)
        
        # Clean up multiple whitespace characters and normalize spaces
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
    
    def _dynamic_search_business_description(self, root: ET.Element) -> Optional[str]:
        """
        Dynamic search for business description when standard patterns fail
        
        Args:
            root: XBRL root element
            
        Returns:
            Business description text or None
        """
        business_candidates = []
        
        # Keywords indicating business description-related data
        business_keywords = [
            # Japanese terms (romanized)
            'jigyou', 'jigyo', 'jigyounaiyo', 'jigyo_naiyo',
            'zigyou', 'zigyo', 'zigyounaiyo', 'zigyo_naiyo',
            'business', 'description', 'outline', 'overview',
            'summary', 'content', 'nature', 'main', 'principal',
            'core', 'profile', 'activities', 'corporate',
            'company', 'enterprise', 'operation', 'service',
            'segment', 'division', 'sector', 'industry',
            'field', 'area', 'domain', 'scope', 'activity',
            
            # More specific business terms
            'BusinessRisks', 'BusinessEnvironment', 'BusinessModel',
            'BusinessStrategy', 'BusinessPlan', 'BusinessStatus',
            'BusinessConditions', 'BusinessOutlook', 'BusinessResults',
            'BusinessPerformance', 'BusinessTrends', 'BusinessPolicy',
            
            # Company description terms
            'CompanyOverview', 'CorporateOverview', 'OrganizationOverview',
            'CompanyInformation', 'CorporateInformation', 'CompanyData',
            'CorporateData', 'CompanyDetails', 'CorporateDetails',
            
            # Report section terms
            'ManagementDiscussion', 'ManagementAnalysis', 'ExecutiveSummary',
            'CompanyDescription', 'CorporateDescription', 'AboutCompany',
            'AboutCorporation', 'WhatWeDo', 'OurBusiness'
        ]
        
        # Search through all elements for text content
        for elem in root.iter():
            if elem.tag and elem.text:
                tag_name = elem.tag
                
                # Remove namespace prefix for matching
                local_name = tag_name.split('}')[-1] if '}' in tag_name else tag_name
                
                # Check if tag contains business-related keywords
                for keyword in business_keywords:
                    if keyword.lower() in local_name.lower():
                        text_content = elem.text.strip()
                        
                        # Remove HTML tags and entities from text
                        text_content = self._sanitize_html(text_content)
                        
                        # Filter for meaningful business descriptions
                        if len(text_content) >= 20:  # At least 20 characters
                            context_ref = elem.get('contextRef', '')
                            
                            # Skip NonConsolidatedMember contexts (individual company data)
                            if 'NonConsolidatedMember' in context_ref:
                                continue
                            
                            priority = self._calculate_business_description_priority(local_name, context_ref, text_content)
                            business_candidates.append((text_content, priority, local_name, context_ref))
                            
                        break
        
        # Sort by priority (higher is better) and return the best match
        if business_candidates:
            business_candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = business_candidates[0]
            print(f"Dynamic business description search found text from tag '{best_match[2]}' (context: {best_match[3]})")
            return best_match[0]
        
        return None
    
    def _calculate_business_description_priority(self, tag_name: str, context_ref: str, text: str) -> int:
        """
        Calculate priority score for business description candidate
        
        Args:
            tag_name: Local tag name
            context_ref: Context reference
            text: Text content
            
        Returns:
            Priority score (higher is better)
        """
        priority = 0
        
        # Higher priority for current year context
        if 'CurrentYear' in context_ref:
            priority += 15
        elif 'Current' in context_ref:
            priority += 10
        
        # Higher priority for exact business description tags
        if any(term in tag_name.lower() for term in ['descriptionofbusiness', 'businessdescription', 'outlineofbusiness']):
            priority += 20
        elif any(term in tag_name.lower() for term in ['businessoverview', 'overviewofbusiness', 'businesssummary']):
            priority += 18
        elif any(term in tag_name.lower() for term in ['businesscontent', 'contentofbusiness', 'natureofbusiness']):
            priority += 16
        elif any(term in tag_name.lower() for term in ['mainbusiness', 'principalbusiness', 'corebusiness']):
            priority += 14
        elif any(term in tag_name.lower() for term in ['companyprofile', 'corporateprofile']):
            priority += 12
        elif any(term in tag_name.lower() for term in ['businessactivities', 'activitiesofbusiness']):
            priority += 10
        elif 'business' in tag_name.lower():
            priority += 8
        
        # Higher priority for consolidated in tag name
        if 'consolidated' in tag_name.lower():
            priority += 5
        
        # Prefer longer, more descriptive text
        text_length = len(text)
        if text_length >= 100:
            priority += 10
        elif text_length >= 50:
            priority += 8
        elif text_length >= 30:
            priority += 5
        elif text_length >= 20:
            priority += 3
        
        # Higher priority for text that looks like business descriptions
        business_indicators = ['事業', '業務', '営業', '製造', '販売', '開発', 'サービス', '提供', '展開', 'グループ', '会社']
        japanese_business_count = sum(1 for indicator in business_indicators if indicator in text)
        priority += japanese_business_count * 3
        
        english_business_indicators = ['business', 'service', 'product', 'company', 'group', 'operation', 'manufacturing', 'development']
        english_business_count = sum(1 for indicator in english_business_indicators if indicator.lower() in text.lower())
        priority += english_business_count * 2
        
        return priority