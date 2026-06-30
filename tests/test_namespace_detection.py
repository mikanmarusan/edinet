"""
Tests for per-document XBRL taxonomy namespace detection and XML hardening.

Covers issue #182:
- detect_taxonomy_namespaces resolves the taxonomy edition actually used by a
  filing (editions coexist by fiscal period) and falls back to static defaults.
- The XBRL_NAMESPACES re-export from lib.xbrl_parser stays intact.
- The parse path is hardened against XML entity-expansion ("billion laughs").
"""

import io
import unittest
import zipfile

from defusedxml.ElementTree import fromstring as defused_fromstring

from lib.edinet_common import (
    detect_taxonomy_namespaces,
    XBRL_NAMESPACES,
    EXPECTED_EQUITY_CHANGES,
    XBRLParsingError,
)
from lib.xbrl_parser import XBRLParser, FinancialDataExtractor
from lib.xbrl_parser import XBRL_NAMESPACES as REEXPORTED_XBRL_NAMESPACES


NS_2025 = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    b'xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor" '
    b'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor" '
    b'xmlns:jpdei_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor">'
    b'</xbrli:xbrl>'
)

NS_2024 = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    b'xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor" '
    b'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor">'
    b'</xbrli:xbrl>'
)

NS_ABSENT = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<root xmlns="http://www.example.com/none"></root>'
)

# Same 2025 edition, but with single-quoted xmlns values (XML permits both).
NS_2025_SINGLE_QUOTED = (
    b"<?xml version='1.0' encoding='UTF-8'?>"
    b"<xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance' "
    b"xmlns:jpcrp_cor='http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor' "
    b"xmlns:jppfs_cor='http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor'>"
    b"</xbrli:xbrl>"
)

# A 2025-edition document carrying both NetAssets (純資産合計) and the larger
# ShareholdersEquity (株主資本) under a current-year context. Mirrors sec 1301.
EQUITY_2025_DOC = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    b'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor">'
    b'<xbrli:context id="CurrentYearInstant">'
    b'<xbrli:period><xbrli:instant>2025-03-31</xbrli:instant></xbrli:period>'
    b'</xbrli:context>'
    b'<jppfs_cor:NetAssets contextRef="CurrentYearInstant">63189000000</jppfs_cor:NetAssets>'
    b'<jppfs_cor:ShareholdersEquity contextRef="CurrentYearInstant">78868000000</jppfs_cor:ShareholdersEquity>'
    b'</xbrli:xbrl>'
)

# Classic "billion laughs" entity-expansion payload.
BILLION_LAUGHS = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE lolz ['
    b'  <!ENTITY lol "lol">'
    b'  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
    b'  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">'
    b'  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">'
    b']>'
    b'<lolz>&lol4;</lolz>'
)


def _make_xbrl_zip(xbrl_bytes: bytes) -> bytes:
    """Wrap raw XBRL bytes in a ZIP that find_main_xbrl recognizes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            'XBRL/PublicDoc/jpcrp030000-asr-001_E00000-000_2025-03-31_01_2025-06-30.xbrl',
            xbrl_bytes,
        )
    return buffer.getvalue()


class TestDetectTaxonomyNamespaces(unittest.TestCase):
    """detect_taxonomy_namespaces resolves the edition used by each document."""

    def test_detects_2025_edition(self):
        """A 2025 inline doc resolves to 2025-11-01 taxonomy URIs."""
        ns = detect_taxonomy_namespaces(NS_2025)
        self.assertEqual(
            ns['jpcrp_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor',
        )
        self.assertEqual(
            ns['jppfs_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor',
        )

    def test_detects_2024_edition(self):
        """A 2024 doc resolves to 2024-11-01 taxonomy URIs."""
        ns = detect_taxonomy_namespaces(NS_2024)
        self.assertEqual(
            ns['jpcrp_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor',
        )
        self.assertEqual(
            ns['jppfs_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor',
        )

    def test_falls_back_to_static_defaults(self):
        """When no jpcrp/jppfs xmlns is present, the static defaults are returned."""
        ns = detect_taxonomy_namespaces(NS_ABSENT)
        self.assertEqual(ns, XBRL_NAMESPACES)

    def test_does_not_mutate_static_defaults(self):
        """The static XBRL_NAMESPACES map is never mutated by detection."""
        before = dict(XBRL_NAMESPACES)
        detect_taxonomy_namespaces(NS_2025)
        self.assertEqual(XBRL_NAMESPACES, before)

    def test_fail_safe_on_garbage_input(self):
        """Non-XML bytes never raise; static defaults are returned."""
        ns = detect_taxonomy_namespaces(b'\x00\x01not xml at all')
        self.assertEqual(ns, XBRL_NAMESPACES)

    def test_detects_single_quoted_namespaces(self):
        """Single-quoted xmlns values resolve identically to double-quoted ones."""
        ns = detect_taxonomy_namespaces(NS_2025_SINGLE_QUOTED)
        self.assertEqual(
            ns['jpcrp_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor',
        )
        self.assertEqual(
            ns['jppfs_cor'],
            'http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor',
        )


class TestNamespaceReexport(unittest.TestCase):
    """The XBRL_NAMESPACES re-export from lib.xbrl_parser must stay importable."""

    def test_reexport_matches(self):
        self.assertEqual(REEXPORTED_XBRL_NAMESPACES, XBRL_NAMESPACES)


class TestEntityExpansionHardening(unittest.TestCase):
    """The parse path rejects entity-expansion payloads instead of expanding them."""

    def test_billion_laughs_raises(self):
        parser = XBRLParser()
        zip_bytes = _make_xbrl_zip(BILLION_LAUGHS)
        with self.assertRaises(XBRLParsingError):
            parser.parse_financial_data(
                zip_bytes,
                sec_code='0000',
                filer_name='Test Co',
                doc_id='TESTDOC',
                period_end='2025-03-31',
                issued_date='2025-06-30',
            )


class TestEquityNetAssetsExtraction(unittest.TestCase):
    """NetAssets is selected over ShareholdersEquity, and only when the
    per-document namespace map reaches extraction."""

    def test_netassets_selected_with_detected_namespace(self):
        """With the detected 2025 namespace, equity resolves to NetAssets."""
        extractor = FinancialDataExtractor()
        extractor.namespaces = detect_taxonomy_namespaces(EQUITY_2025_DOC)
        root = defused_fromstring(EQUITY_2025_DOC)
        value = extractor.extract_numeric_value_with_context(
            root, extractor.patterns['equity'])
        self.assertEqual(value, EXPECTED_EQUITY_CHANGES['1301']['expected_equity'])

    def test_static_namespace_misses_2025_edition(self):
        """With only the static 2024 defaults, the 2025-edition element is not
        found - proving the per-document namespace assignment is load-bearing."""
        extractor = FinancialDataExtractor()
        extractor.namespaces = dict(XBRL_NAMESPACES)  # static defaults (2024-11-01)
        root = defused_fromstring(EQUITY_2025_DOC)
        value = extractor.extract_numeric_value_with_context(
            root, extractor.patterns['equity'])
        self.assertIsNone(value)

    def test_allowlist_documents_expected_change(self):
        """The allowlist records sec 1301's NetAssets concept and value."""
        entry = EXPECTED_EQUITY_CHANGES['1301']
        self.assertEqual(entry['concept'], 'NetAssets')
        self.assertEqual(entry['expected_equity'], 63189000000)


if __name__ == '__main__':
    unittest.main()
