"""Shared helpers for the XBRL fixture-based regression tests (issue #187).

The fixtures under ``tests/fixtures/xbrl/`` are synthetic: every figure is an
obviously-fake round number for a fictitious filer, never a real company's
reported value. They are round-trip anchors - a value placed in the fixture is
asserted to come back out - validating extraction wiring across taxonomy
editions (2024-11-01 / 2025-11-01), accounting standards (JGAAP / IFRS), a
bank-style filer, and a consolidated-vs-parent context split.
"""
import io
import os
import zipfile

from lib.xbrl_parser import XBRLParser

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'xbrl')

# Synthetic market data shared by every fixture so per/pbr/ev are deterministic
# and reproducible offline (the market fetcher is never called here).
SYNTHETIC_YAHOO = {'stockPrice': 750.0, 'marketCapitalization': 75000000000}

# Fixtures exercised by the golden harness.
FIXTURES = [
    'consolidated_jgaap_2024.xbrl',
    'consolidated_jgaap_2025.xbrl',
    'ifrs_2024.xbrl',
    'bank_2024.xbrl',
    'consolidated_vs_parent_2024.xbrl',
]

# Financial fields the golden harness tracks for regressions.
GOLDEN_FIELDS = [
    'netSales', 'operatingIncome', 'ordinaryIncome', 'netIncome', 'equity',
    'cash', 'debt', 'eps', 'bps', 'per', 'pbr', 'outstandingShares', 'ev',
    'marketCapitalization', 'stockPrice',
]


def fixture_path(name):
    """Absolute path to a fixture file under tests/fixtures/xbrl/."""
    return os.path.join(FIXTURE_DIR, name)


def read_fixture_bytes(name):
    """Raw XBRL bytes of a fixture (for namespace-detection tests)."""
    with open(fixture_path(name), 'rb') as f:
        return f.read()


def _zip_fixture(name):
    """Wrap a fixture's XBRL in the PublicDoc ZIP layout the parser expects."""
    raw = read_fixture_bytes(name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('PublicDoc/doc.xbrl', raw)
    return buf.getvalue()


def parse_fixture(name, yahoo_data=None, doc_id='S100TEST'):
    """Parse a fixture into the consolidated financial-data dict.

    Uses SYNTHETIC_YAHOO by default; pass yahoo_data=None explicitly via the
    sentinel below to omit market data.
    """
    parser = XBRLParser()
    yd = dict(SYNTHETIC_YAHOO) if yahoo_data is None else yahoo_data
    return parser.parse_financial_data(
        _zip_fixture(name),
        sec_code='9999',
        filer_name='テスト株式会社',
        doc_id=doc_id,
        period_end='2024-03-31',
        issued_date='2024-06-28',
        yahoo_data=yd,
    )
