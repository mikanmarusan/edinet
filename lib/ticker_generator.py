import yaml
import os

def get_ticker_from_security_code(secCode):
    config_path = os.path.join(os.path.dirname(__file__), '../config/stock_exchange_mapping.yml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        mapping = yaml.safe_load(f)
    
    stock_exchanges = mapping.get('stock_exchanges', {})
    
    if secCode in stock_exchanges:
        exchange = stock_exchanges[secCode]
        return f"{secCode}.{exchange}"
    else:
        return f"{secCode}.T"