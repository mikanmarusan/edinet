def generate_yahoo_finance_urls(ticker):
    base_url = "https://finance.yahoo.co.jp/quote/"
    
    return {
        'profile': f"{base_url}{ticker}/profile",
        'performance': f"{base_url}{ticker}/performance?styl=performance",
        'financials': f"{base_url}{ticker}/performance?styl=financials"
    }