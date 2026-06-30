"""
Market-data fetcher for EDINET financial documents (issue #185, PR4).

Fetches ONLY market data (stockPrice, marketCapitalization in yen) from the
Yahoo Finance base quote page via plain `requests` + BeautifulSoup. The base
quote page is server-side rendered, so no headless browser (Playwright) is
needed. Financial-statement fields come from EDINET XBRL (PR1-3); market fields
degrade to null (with a WARNING) rather than aborting a company's row.

Yahoo scraping is ToS-prohibited and treated here as a null-tolerant interim
bridge pending migration to an official market-data source (future milestone).
"""

import logging
import random
import re
import time
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from .ticker_generator import get_ticker_from_security_code
from .url_generator import generate_yahoo_finance_url

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_MIN_REQUEST_INTERVAL = 1.0  # seconds; >= 1 request/second
_REQUEST_TIMEOUT = 15  # seconds
_MAX_RETRIES = 3

_NUM_RE = re.compile(r"[\d,]+(?:\.\d+)?")

# Module-level state: reused session + pacing clock. The fetch loop is
# single-threaded; if it is ever parallelized, _pace() and market_null_counts
# would need synchronization.
_session: Optional[requests.Session] = None
_last_request_ts = 0.0

# Run-summary counters: how many companies had each market field null.
market_null_counts: Dict[str, int] = {"stockPrice": 0, "marketCapitalization": 0}


def reset_market_null_counts() -> None:
    """Reset the per-run null counters (call once at the start of a batch run)."""
    market_null_counts["stockPrice"] = 0
    market_null_counts["marketCapitalization"] = 0


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": _USER_AGENT})
    return _session


def _pace() -> None:
    """Enforce >= 1 request/second with a little jitter on the shared session."""
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    wait = _MIN_REQUEST_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait + random.uniform(0.0, 0.4))
    _last_request_ts = time.time()


def _fetch_html(url: str) -> Optional[str]:
    """GET the base quote page with pacing and 403/429 backoff. None on failure.

    Default TLS verification is kept (no verify=False / ignore_https_errors).
    """
    session = _get_session()
    for attempt in range(_MAX_RETRIES + 1):
        _pace()
        try:
            resp = session.get(url, timeout=_REQUEST_TIMEOUT)
        except requests.RequestException as e:
            logger.warning("Yahoo fetch error for %s: %s", url, e)
            return None

        if resp.status_code in (403, 429):
            backoff = (2 ** attempt) + random.uniform(0.0, 1.0)
            logger.warning(
                "Yahoo returned HTTP %s for %s; backing off %.1fs (attempt %d)",
                resp.status_code, url, backoff, attempt + 1,
            )
            time.sleep(backoff)
            continue

        if resp.status_code != 200:
            logger.warning("Yahoo returned HTTP %s for %s", resp.status_code, url)
            return None

        return resp.text

    logger.warning("Yahoo fetch exhausted retries for %s", url)
    return None


def _parse_stock_price(soup: BeautifulSoup) -> Optional[float]:
    """Current price from the price board.

    Anchored on the semantic class fragments (the hash suffix varies across Yahoo
    deploys, the semantic prefix is stable). The lookup is scoped to the price
    block (`CommonPriceBoard__priceBlock_`) so sibling figures elsewhere on the
    page (始値/高値/安値, 前日終値, which live in labelled DataListItems) cannot be
    mistaken for the current price.
    """
    scope = soup.select_one('[class*="CommonPriceBoard__priceBlock_"]') or soup
    el = scope.select_one('[class*="CommonPriceBoard__price_"]')
    if el is None:
        return None
    match = _NUM_RE.search(el.get_text(strip=True))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _enclosing_data_list_item(node):
    """Walk up to the nearest DataListItem *block* container so a label's value
    cannot bleed in from an adjacent metric.

    Matches the BEM block class (`_DataListItem_<hash>`) and skips its elements
    (`_DataListItem__name_`, `_DataListItem__data_`), which also contain the
    fragment "DataListItem_".
    """
    while node is not None:
        for c in (node.get("class") or []):
            if "DataListItem_" in c and "DataListItem__" not in c:
                return node
        node = node.parent
    return None


def _parse_market_cap_yen(soup: BeautifulSoup) -> Optional[int]:
    """時価総額 (market capitalization) in yen.

    Anchored on the Japanese label "時価総額" (stable across deploys), reading the
    value within its DataListItem. Yahoo reports it in 百万円 (millions of yen).
    """
    for span in soup.find_all("span"):
        if span.get_text(strip=True) != "時価総額":
            continue
        # Scope to the label's own DataListItem so an adjacent metric's number or
        # unit cannot bleed in.
        container = _enclosing_data_list_item(span) or span.parent
        if container is None:
            return None
        # Read the value from the DataListItem's data sub-element when present, so
        # a digit in the interstitial "用語" tooltip cannot be captured instead.
        data_el = container.select_one('[class*="DataListItem__data_"]')
        if data_el is not None:
            after = data_el.get_text(" ", strip=True)
        else:
            after = container.get_text(" ", strip=True).split("時価総額", 1)[-1]
        match = _NUM_RE.search(after)
        if not match:
            return None
        try:
            value = float(match.group(0).replace(",", ""))
        except ValueError:
            return None
        if "百万円" in after:
            return int(value * 1_000_000)
        if "円" in after:
            return int(value)
        # No explicit unit found: Yahoo's 時価総額 is conventionally 百万円, but
        # warn because a wrong unit would be a silent 1,000,000x error.
        logger.warning(
            "時価総額 unit not found near value %s; assuming 百万円", match.group(0)
        )
        return int(value * 1_000_000)
    return None


def parse_market_data(html: str) -> Dict[str, Any]:
    """Parse stockPrice and marketCapitalization (yen) from base-quote-page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return {
        "stockPrice": _parse_stock_price(soup),
        "marketCapitalization": _parse_market_cap_yen(soup),
    }


def get_financial_data(secCode: str, periodEnd: str) -> Dict[str, Any]:
    """Fetch market data for a security from the Yahoo base quote page.

    Returns only {stockPrice, marketCapitalization} (yen). Financial-statement
    fields are sourced from EDINET XBRL elsewhere. On any failure (network error,
    soft-block, structure change) the missing market fields are null and a
    WARNING naming them is logged; the company's row is never aborted.

    `periodEnd` is accepted for signature compatibility; the base quote page is a
    point-in-time snapshot and does not use it.
    """
    data: Dict[str, Any] = {"stockPrice": None, "marketCapitalization": None}

    ticker = get_ticker_from_security_code(secCode)
    url = generate_yahoo_finance_url(ticker)
    html = _fetch_html(url)

    if html is None:
        logger.warning(
            "No market data for %s (%s): stockPrice, marketCapitalization set to null",
            secCode, ticker,
        )
        market_null_counts["stockPrice"] += 1
        market_null_counts["marketCapitalization"] += 1
        return data

    parsed = parse_market_data(html)
    data["stockPrice"] = parsed["stockPrice"]
    data["marketCapitalization"] = parsed["marketCapitalization"]

    missing = [field for field, value in data.items() if value is None]
    if missing:
        logger.warning(
            "Market data missing for %s (%s): %s set to null",
            secCode, ticker, ", ".join(missing),
        )
        for field in missing:
            market_null_counts[field] += 1

    return data
