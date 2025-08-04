import json
import re
import logging
from playwright.sync_api import sync_playwright

# Setup module logger
logger = logging.getLogger(__name__)


def extract_preloaded_state(page):
    """Extract __PRELOADED_STATE__ from page"""
    try:
        preloaded_state = page.evaluate('() => window.__PRELOADED_STATE__')
        if preloaded_state:
            return preloaded_state
    except:
        pass
    
    # Fallback to regex parsing
    content = page.content()
    pattern = r'window\.__PRELOADED_STATE__\s*=\s*({.+?});?\s*(?:window\.|</script>)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
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
    except:
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
    except:
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
            except:
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
                    except:
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
        
        for row in rows:
            cells = row.query_selector_all('td, th')
            if not cells:
                continue
                
            first_cell = cells[0].text_content().strip()
            
            # Check if this row contains our fiscal period
            if target_period in first_cell or target_year in first_cell:
                # Map column positions to data fields
                try:
                    if len(cells) > 1:
                        value = parse_numeric_value(cells[1].text_content())
                        financial_data['netSales'] = convert_million_to_yen(value)
                    if len(cells) > 4:
                        value = parse_numeric_value(cells[4].text_content())
                        financial_data['operatingIncome'] = convert_million_to_yen(value)
                    # Check multiple columns for ordinary income
                    for col_idx in [5, 6, 7]:
                        if len(cells) > col_idx:
                            value = parse_numeric_value(cells[col_idx].text_content())
                            if value and value not in ['---', 'N/A', '', '—']:
                                try:
                                    float(value)  # Validate it's a number
                                    converted = convert_million_to_yen(value)
                                    if converted is not None:
                                        financial_data['ordinaryIncome'] = converted
                                        break
                                except:
                                    continue
                    if len(cells) > 8:
                        value = parse_numeric_value(cells[8].text_content())
                        financial_data['netIncome'] = convert_million_to_yen(value)
                except Exception:
                    pass
                break
                
    except Exception as e:
        logger.error(f"Error parsing performance data: {e}")


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
                    if len(cells) > 1:  # EPS
                        value = parse_numeric_value(cells[1].text_content())
                        if value not in ['---', 'N/A', '']:
                            try:
                                financial_data['eps'] = float(value)
                            except:
                                financial_data['eps'] = None
                    
                    if len(cells) > 2:  # BPS
                        value = parse_numeric_value(cells[2].text_content())
                        if value not in ['---', 'N/A', '']:
                            try:
                                financial_data['bps'] = float(value)
                            except:
                                financial_data['bps'] = None
                    
                    if len(cells) > 8:  # Debt (有利子負債)
                        value = parse_numeric_value(cells[8].text_content())
                        financial_data['debt'] = convert_million_to_yen(value)
                    
                    if len(cells) > 9:  # Depreciation
                        value = parse_numeric_value(cells[9].text_content())
                        financial_data['depreciation'] = convert_million_to_yen(value)
                    
                    if len(cells) > 10:  # Outstanding shares
                        value = parse_numeric_value(cells[10].text_content())
                        financial_data['outstandingShares'] = convert_thousand_to_shares(value)
                except Exception as cell_error:
                    pass
                break
                
    except Exception as e:
        logger.error(f"Error parsing financial data: {e}")


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
            
            browser.close()
    except Exception as e:
        raise
    
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
