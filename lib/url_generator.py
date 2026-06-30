def generate_yahoo_finance_url(ticker):
    """Return the Yahoo Finance base quote URL for a ticker.

    Only the SSR base quote page is fetched now (issue #185); the former
    profile/performance/financials sub-pages (Playwright-scraped) are gone.
    """
    return f"https://finance.yahoo.co.jp/quote/{ticker}"
