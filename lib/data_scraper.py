import json
import re
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

# Setup module logger
logger = logging.getLogger(__name__)


def extract_preloaded_state(page):
    """Extract __PRELOADED_STATE__ from page"""
    try:
        preloaded_state = page.evaluate('() => window.__PRELOADED_STATE__')
        if preloaded_state:
            return preloaded_state
    except PlaywrightError as e:
        logger.debug(f"Failed to evaluate JavaScript for __PRELOADED_STATE__: {e}")
    except Exception as e:
        logger.debug(f"Unexpected error evaluating __PRELOADED_STATE__: {e}")
    
    # Fallback to regex parsing
    content = page.content()
    pattern = r'window\.__PRELOADED_STATE__\s*=\s*({.+?});?\s*(?:window\.|</script>)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in __PRELOADED_STATE__: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error parsing __PRELOADED_STATE__ JSON: {e}")
    
    return {}


def parse_numeric_value(value):
    """Remove commas and units from numeric values"""
    if isinstance(value, str):
        return value.replace(',', '').replace('円', '').replace('人', '').replace('株', '').strip()
    return str(value)


def convert_million_to_yen(value_str):
    """Convert million yen to yen (e.g., '51121' -> 51121000000)"""
    try:
        # Handle special cases like '---' or 'N/A'
        if value_str in ['---', 'N/A', '']:
            return None
        
        # For negative values
        is_negative = value_str.startswith('-')
        if is_negative:
            value_str = value_str[1:]
        
        # Convert to number and multiply by 1,000,000
        value = int(value_str)
        result = value * 1000000
        
        # Add negative sign back if needed
        return -result if is_negative else result
    except ValueError as e:
        logger.debug(f"Invalid numeric value for million to yen conversion: '{value_str}' - {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error in million to yen conversion: '{value_str}' - {e}")
        return None


def convert_thousand_to_shares(value_str):
    """Convert thousand shares to shares (e.g., '58162' -> 58162000)"""
    try:
        # Handle special cases
        if value_str in ['---', 'N/A', '']:
            return None
        
        # Convert to number and multiply by 1,000
        value = int(value_str)
        return value * 1000
    except ValueError as e:
        logger.debug(f"Invalid numeric value for thousand to shares conversion: '{value_str}' - {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error in thousand to shares conversion: '{value_str}' - {e}")
        return None


def extract_profile_data(page, financial_data):
    """Extract company profile data from PRELOADED_STATE"""
    state = extract_preloaded_state(page)
    
    # Extract stock price
    if 'mainStocksPriceBoard' in state:
        price_board = state['mainStocksPriceBoard'].get('priceBoard', {})
        if 'price' in price_board:
            try:
                financial_data['stockPrice'] = float(parse_numeric_value(price_board['price']))
            except ValueError as e:
                logger.debug(f"Invalid stock price value: {price_board.get('price')} - {e}")
                financial_data['stockPrice'] = None
            except Exception as e:
                logger.debug(f"Unexpected error parsing stock price: {e}")
                financial_data['stockPrice'] = None
    
    # Extract company characteristics and employees
    if 'mainStocksProfile' in state:
        profile_items = state['mainStocksProfile'].get('items', [])
        for item in profile_items:
            head = item.get('head', '')
            details = item.get('details', [])
            
            if head == '特色' and details:
                financial_data['characteristic'] = details[0].get('text', '') or None
            elif head == '従業員数（連結）' and details:
                emp_text = details[0].get('text', '')
                emp_match = re.search(r'([\d,]+)人', emp_text)
                if emp_match:
                    try:
                        financial_data['employees'] = int(emp_match.group(1).replace(',', ''))
                    except ValueError as e:
                        logger.debug(f"Invalid employee count value: {emp_match.group(1)} - {e}")
                        financial_data['employees'] = None
                    except Exception as e:
                        logger.debug(f"Unexpected error parsing employee count: {e}")
                        financial_data['employees'] = None


def extract_performance_data(page, periodEnd, financial_data):
    """Extract performance data from PRELOADED_STATE"""
    # Parse periodEnd
    try:
        target_year = periodEnd.split('年')[0]
        target_month = periodEnd.split('年')[1].replace('月期', '')
        target_period = f"{target_year}年{target_month}月期"
    except IndexError:
        # Handle case where periodEnd format is different
        target_period = periodEnd
        target_year = periodEnd.split('年')[0] if '年' in periodEnd else periodEnd
    
    # First, try to extract from PRELOADED_STATE
    state = extract_preloaded_state(page)
    
    # Check for performance data in PRELOADED_STATE
    if 'mainStocksPerformance' in state:
        performance_data = state['mainStocksPerformance']
        
        # Extract financial metrics from the performance data
        if 'items' in performance_data:
            for item in performance_data['items']:
                # Find the row that matches our fiscal period
                period_text = item.get('period', '')
                if target_year in period_text or target_period in period_text:
                    # Extract financial metrics
                    if 'sales' in item:
                        financial_data['netSales'] = convert_million_to_yen(str(item['sales']))
                    if 'operatingIncome' in item:
                        financial_data['operatingIncome'] = convert_million_to_yen(str(item['operatingIncome']))
                    if 'ordinaryIncome' in item:
                        financial_data['ordinaryIncome'] = convert_million_to_yen(str(item['ordinaryIncome']))
                    if 'netIncome' in item:
                        financial_data['netIncome'] = convert_million_to_yen(str(item['netIncome']))
                    return
        
        # Alternative structure - check for table data in PRELOADED_STATE
        if 'tableData' in performance_data:
            table_data = performance_data['tableData']
            for row in table_data:
                if isinstance(row, dict):
                    period_text = row.get('period', '')
                    if target_year in period_text or target_period in period_text:
                        # Map common field names
                        field_mappings = {
                            'revenue': 'netSales',
                            'sales': 'netSales',
                            '売上高': 'netSales',
                            'operatingProfit': 'operatingIncome',
                            'operatingIncome': 'operatingIncome',
                            '営業利益': 'operatingIncome',
                            'ordinaryProfit': 'ordinaryIncome',
                            'ordinaryIncome': 'ordinaryIncome',
                            '経常利益': 'ordinaryIncome',
                            'netProfit': 'netIncome',
                            'netIncome': 'netIncome',
                            '純利益': 'netIncome'
                        }
                        
                        for key, value in row.items():
                            if key in field_mappings and value:
                                mapped_field = field_mappings[key]
                                financial_data[mapped_field] = convert_million_to_yen(str(value))
                        return
    
    # Fallback to table parsing if PRELOADED_STATE doesn't contain the data
    try:
        tables = page.query_selector_all('table')
        if not tables:
            return
            
        # First table contains performance data
        rows = tables[0].query_selector_all('tr')
        
        # Extract headers to map column positions
        column_mapping = {}
        
        # Define comprehensive header patterns for robust matching
        header_patterns = {
            'netSales': [
                '売上高', '売上', 'sales', 'revenue', '収益', '営業収益',
                'total revenue', 'net sales', '売上収益'
            ],
            'operatingIncome': [
                '営業利益', 'operating income', 'operating profit', 
                '営業損益', 'operating earnings', '事業利益'
            ],
            'ordinaryIncome': [
                '経常利益', 'ordinary income', 'ordinary profit',
                '経常損益', 'recurring profit', 'recurring income'
            ],
            'netIncome': [
                '純利益', '当期純利益', 'net income', 'net profit',
                '親会社株主に帰属する当期純利益', 'net earnings',
                'profit attributable', '最終利益', '当期利益'
            ]
        }
        
        # First pass: check for header rows (th elements)
        for idx, row in enumerate(rows[:5]):  # Check first 5 rows for headers
            cells = row.query_selector_all('th')
            if cells and len(cells) > 1:
                for col_idx, cell in enumerate(cells):
                    header_text = cell.text_content().strip().lower()
                    # Check against all patterns
                    for field_name, patterns in header_patterns.items():
                        if any(pattern.lower() in header_text for pattern in patterns):
                            if field_name not in column_mapping:
                                column_mapping[field_name] = col_idx
                                logger.debug(f"Mapped header '{header_text}' to {field_name} at column {col_idx}")
                if column_mapping:
                    break
        
        # Second pass: check td cells for header-like content if no th headers found
        if not column_mapping:
            for row in rows[:5]:  # Check first 5 rows
                cells = row.query_selector_all('td')
                if cells and len(cells) > 1:
                    # Check if this looks like a header row (contains text patterns)
                    potential_headers = []
                    for col_idx, cell in enumerate(cells):
                        text = cell.text_content().strip()
                        for field_name, patterns in header_patterns.items():
                            if any(pattern.lower() in text.lower() for pattern in patterns):
                                if field_name not in column_mapping:
                                    column_mapping[field_name] = col_idx
                                    logger.debug(f"Mapped cell text '{text}' to {field_name} at column {col_idx}")
                                    potential_headers.append(field_name)
                    if len(potential_headers) >= 2:  # Found at least 2 headers, likely a header row
                        break
        
        # Parse data rows
        for row in rows:
            cells = row.query_selector_all('td, th')
            if not cells:
                continue
                
            first_cell = cells[0].text_content().strip()
            
            # Check if this row contains our fiscal period
            if target_period in first_cell or target_year in first_cell:
                try:
                    if column_mapping:
                        # Use header-based mapping with validation
                        extracted_count = 0
                        for field_name, col_idx in column_mapping.items():
                            if col_idx < len(cells):
                                value = parse_numeric_value(cells[col_idx].text_content())
                                if field_name in ['netSales', 'operatingIncome', 'ordinaryIncome', 'netIncome']:
                                    converted = convert_million_to_yen(value)
                                    if converted is not None:
                                        # Validate: netSales should be positive, but profits can be negative
                                        if field_name == 'netSales' and converted <= 0:
                                            logger.warning(f"Skipped non-positive netSales value: {converted}")
                                        else:
                                            financial_data[field_name] = converted
                                            extracted_count += 1
                                            logger.debug(f"Extracted {field_name}: {converted} from column {col_idx}")
                        
                        if extracted_count == 0:
                            logger.warning(f"No valid financial data extracted using column mapping for period {target_period}")
                    else:
                        # If no column mapping found, log warning and skip heuristic extraction
                        logger.warning(f"No column headers identified for table parsing. Skipping row for period {target_period}")
                        # We intentionally don't fall back to positional indexing to avoid fragile extraction
                            
                except PlaywrightTimeoutError as e:
                    logger.warning(f"Timeout while parsing performance data for period {target_period}: {e}")
                except PlaywrightError as e:
                    logger.error(f"Playwright error accessing page elements for period {target_period}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error parsing performance data for period {target_period}: {e}")
                break
                
    except PlaywrightTimeoutError as e:
        logger.warning(f"Timeout while extracting performance data for period {periodEnd}: {e}")
    except PlaywrightError as e:
        logger.error(f"Playwright error in extract_performance_data for period {periodEnd}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in extract_performance_data for period {periodEnd}: {e}")


def extract_financial_data(page, periodEnd, financial_data):
    """Extract financial data from table"""
    # Parse periodEnd
    try:
        target_year = periodEnd.split('年')[0]
        target_month = periodEnd.split('年')[1].replace('月期', '')
        target_period = f"{target_year}年{target_month}月期"
    except IndexError:
        # Handle case where periodEnd format is different
        target_period = periodEnd
    
    try:
        tables = page.query_selector_all('table')
        if not tables:
            return
            
        # First table contains financial data
        rows = tables[0].query_selector_all('tr')
        
        # Extract headers to map column positions
        column_mapping = {}
        
        # Define header patterns for financial metrics
        header_patterns = {
            'eps': ['eps', '1株当たり利益', '1株利益', 'earnings per share', '基本的1株当たり'],
            'bps': ['bps', '1株当たり純資産', '1株純資産', 'book value per share', '純資産/株'],
            'debt': ['有利子負債', '負債', 'debt', 'interest-bearing debt', '借入金'],
            'depreciation': ['減価償却', '償却費', 'depreciation', 'amortization'],
            'outstandingShares': ['発行済株式数', '株式数', 'shares outstanding', '発行済み株式', 'outstanding shares']
        }
        
        # First pass: check for header rows
        for idx, row in enumerate(rows[:5]):  # Check first 5 rows for headers
            cells = row.query_selector_all('th, td')
            if cells and len(cells) > 1:
                for col_idx, cell in enumerate(cells):
                    header_text = cell.text_content().strip().lower()
                    # Check against all patterns
                    for field_name, patterns in header_patterns.items():
                        if any(pattern.lower() in header_text for pattern in patterns):
                            if field_name not in column_mapping:
                                column_mapping[field_name] = col_idx
                                logger.debug(f"Mapped financial header '{header_text}' to {field_name} at column {col_idx}")
                if len(column_mapping) >= 2:  # Found at least 2 headers
                    break
        
        for row in rows:
            cells = row.query_selector_all('td, th')
            if not cells:
                continue
                
            first_cell = cells[0].text_content().strip()
            
            # Check if this row contains our fiscal period
            # Also check for partial matches due to format differences
            if target_period in first_cell or target_year in first_cell:
                
                # Map column positions to data fields
                try:
                    if column_mapping:
                        # Use header-based mapping
                        extracted_count = 0
                        for field_name, col_idx in column_mapping.items():
                            if col_idx < len(cells):
                                value = parse_numeric_value(cells[col_idx].text_content())
                                if value not in ['---', 'N/A', '', '—']:
                                    try:
                                        if field_name in ['eps', 'bps']:
                                            financial_data[field_name] = float(value)
                                            extracted_count += 1
                                        elif field_name == 'debt':
                                            converted = convert_million_to_yen(value)
                                            if converted is not None and converted >= 0:
                                                financial_data[field_name] = converted
                                                extracted_count += 1
                                        elif field_name == 'depreciation':
                                            converted = convert_million_to_yen(value)
                                            if converted is not None and converted >= 0:
                                                financial_data[field_name] = converted
                                                extracted_count += 1
                                        elif field_name == 'outstandingShares':
                                            converted = convert_thousand_to_shares(value)
                                            if converted is not None and converted > 0:
                                                financial_data[field_name] = converted
                                                extracted_count += 1
                                        logger.debug(f"Extracted {field_name}: {financial_data.get(field_name)} from column {col_idx}")
                                    except ValueError as e:
                                        logger.debug(f"Invalid {field_name} value for period {target_period}: {value} - {e}")
                                    except Exception as e:
                                        logger.debug(f"Unexpected error parsing {field_name} for period {target_period}: {e}")
                        
                        if extracted_count == 0:
                            logger.warning(f"No valid financial metrics extracted using column mapping for period {target_period}")
                    else:
                        # No column mapping found - log warning
                        logger.warning(f"No column headers identified for financial data table. Skipping extraction for period {target_period}")
                except PlaywrightTimeoutError as e:
                    logger.warning(f"Timeout while parsing financial data cells for period {target_period}: {e}")
                except PlaywrightError as e:
                    logger.error(f"Playwright error accessing table cells for period {target_period}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error parsing financial data cells for period {target_period}: {e}")
                break
                
    except PlaywrightTimeoutError as e:
        logger.warning(f"Timeout while extracting financial data for period {periodEnd}: {e}")
    except PlaywrightError as e:
        logger.error(f"Playwright error in extract_financial_data for period {periodEnd}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in extract_financial_data for period {periodEnd}: {e}")


def get_financial_data(secCode, periodEnd):
    """Main function to get financial data for a security"""
    from .ticker_generator import get_ticker_from_security_code
    from .url_generator import generate_yahoo_finance_urls
    
    ticker = get_ticker_from_security_code(secCode)
    urls = generate_yahoo_finance_urls(ticker)
    
    financial_data = {}
    
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # Profile page - Extract company info and stock price
            page.goto(urls['profile'], wait_until='networkidle')
            extract_profile_data(page, financial_data)
            
            # Performance page - Extract revenue and profit data
            page.goto(urls['performance'], wait_until='networkidle')
            extract_performance_data(page, periodEnd, financial_data)
            
            # Financials page - Extract per-share metrics and other financial data
            page.goto(urls['financials'], wait_until='networkidle')
            extract_financial_data(page, periodEnd, financial_data)
            
            # Browser is automatically closed by the context manager
            
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout error for company {secCode} (period: {periodEnd}): {e}")
        raise RuntimeError(f"Failed to scrape data for {secCode}: timeout occurred - {str(e)}")
    except PlaywrightError as e:
        logger.error(f"Playwright error for company {secCode} (period: {periodEnd}): {e}")
        raise RuntimeError(f"Browser operation failed for {secCode}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error for company {secCode} (period: {periodEnd}): {e}")
        raise RuntimeError(f"Failed to get financial data for {secCode}: {str(e)}")
    
    # Ensure all expected fields are present (set to None if missing)
    expected_fields = [
        'stockPrice', 'characteristic', 'employees', 'netSales', 
        'operatingIncome', 'ordinaryIncome', 'netIncome', 'eps', 'bps', 
        'depreciation', 'outstandingShares', 'debt'
    ]
    
    for field in expected_fields:
        if field not in financial_data:
            financial_data[field] = None
    
    return financial_data
