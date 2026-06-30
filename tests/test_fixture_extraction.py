"""Fixture-based extraction coverage across taxonomy editions and structures
(issue #187, acceptance criterion 1).

Complements the golden harness with explicit behavioral assertions:
- cross-edition determinism (2024-11-01 vs 2025-11-01 extract identically),
- consolidated data wins over parent-only data,
- a bank/insurer structure extracts without crashing,
- docURL is produced for fixture-driven records.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from lib.edinet_common import detect_taxonomy_namespaces
from lib.xbrl_parser import XBRLParser
from _xbrl_fixture_utils import GOLDEN_FIELDS, parse_fixture, read_fixture_bytes


class TestCrossEditionDeterminism(unittest.TestCase):
    def test_2024_and_2025_editions_detect_their_namespace(self):
        ns_2024 = detect_taxonomy_namespaces(read_fixture_bytes('consolidated_jgaap_2024.xbrl'))
        ns_2025 = detect_taxonomy_namespaces(read_fixture_bytes('consolidated_jgaap_2025.xbrl'))
        self.assertIn('jppfs/2024-11-01', ns_2024['jppfs_cor'])
        self.assertIn('jppfs/2025-11-01', ns_2025['jppfs_cor'])

    def test_editions_extract_identical_financials(self):
        """The same facts under different taxonomy editions must extract to the
        same values - extraction is local-name based and edition-stable."""
        r2024 = parse_fixture('consolidated_jgaap_2024.xbrl')
        r2025 = parse_fixture('consolidated_jgaap_2025.xbrl')
        for field in GOLDEN_FIELDS:
            self.assertEqual(r2024.get(field), r2025.get(field),
                             f'edition drift on {field}: {r2024.get(field)} != {r2025.get(field)}')


class TestConsolidatedWinsOverParent(unittest.TestCase):
    def setUp(self):
        self.result = parse_fixture('consolidated_vs_parent_2024.xbrl')

    def test_net_sales_uses_consolidated_not_parent(self):
        # consolidated NetSales = 70B, parent-only = 40B
        self.assertEqual(self.result['netSales'], 70000000000.0)

    def test_equity_uses_consolidated_not_parent(self):
        # consolidated NetAssets = 35B, parent-only = 20B
        self.assertEqual(self.result['equity'], 35000000000.0)


class TestBankStructure(unittest.TestCase):
    def test_bank_filer_extracts_without_crashing(self):
        result = parse_fixture('bank_2024.xbrl')
        self.assertIsNotNone(result)
        # A bank reports 経常収益/経常利益 (ordinary income) and net assets.
        self.assertEqual(result['ordinaryIncome'], 2000000000.0)
        self.assertEqual(result['equity'], 25000000000.0)


class TestPriorityTieDeterminism(unittest.TestCase):
    """Pin the deterministic secondary sort key (issue #187).

    The tie-break fixture holds two sales candidates with DISTINCT tag
    local-names but IDENTICAL priority, in document order TotalRevenue (44B)
    then NetSales (55B). The winner is therefore decided solely by the secondary
    sort key (tag local-name), not by document/iteration order - which is the
    only scenario the determinism change affects.
    """

    def test_tie_candidates_have_equal_priority(self):
        # Guards the test itself: if these ever stop tying, the fixture no
        # longer exercises the secondary key and must be rebuilt.
        parser = XBRLParser()
        p_netsales = parser._calculate_sales_priority('NetSales', 'CurrentYearDuration', 55000000000)
        p_totalrev = parser._calculate_sales_priority('TotalRevenue', 'CurrentYearDuration', 44000000000)
        self.assertEqual(p_netsales, p_totalrev,
                         'tie-break fixture no longer ties; rebuild it')

    def test_alphabetically_first_tag_wins_the_tie(self):
        # 'NetSales' < 'TotalRevenue', so 55B wins over document-order 44B.
        result = parse_fixture('tie_break_2024.xbrl')
        self.assertEqual(result['netSales'], 55000000000.0)

    def test_selection_is_reproducible(self):
        first = parse_fixture('tie_break_2024.xbrl')['netSales']
        second = parse_fixture('tie_break_2024.xbrl')['netSales']
        self.assertEqual(first, second)


class TestDocURLForFixtures(unittest.TestCase):
    def test_docurl_present_for_valid_docid(self):
        result = parse_fixture('consolidated_jgaap_2024.xbrl', doc_id='S100ABCD')
        self.assertEqual(
            result['docURL'],
            'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100ABCD',
        )


if __name__ == '__main__':
    unittest.main()
