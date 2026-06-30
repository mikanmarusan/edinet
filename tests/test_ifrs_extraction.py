"""IFRS extraction coverage (issue #187, acceptance criterion 2).

An IFRS filer reports equity under the jpigp taxonomy (EquityIFRS) and revenue
via the jpcrp IFRS revenue summary tag, and has NO 経常利益 (ordinary income)
concept - so ordinaryIncome must be null, never fabricated.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from lib.edinet_common import detect_taxonomy_namespaces
from _xbrl_fixture_utils import parse_fixture, read_fixture_bytes

IFRS_FIXTURE = 'ifrs_2024.xbrl'


class TestIFRSExtraction(unittest.TestCase):
    def setUp(self):
        self.result = parse_fixture(IFRS_FIXTURE)

    def test_jpigp_namespace_resolves(self):
        """The IFRS filing's jpigp taxonomy namespace is detected from the
        document, not assumed from a static default."""
        namespaces = detect_taxonomy_namespaces(read_fixture_bytes(IFRS_FIXTURE))
        self.assertIn('jpigp_cor', namespaces)
        self.assertIn('jpigp/2024-11-01', namespaces['jpigp_cor'])

    def test_ordinary_income_is_none_for_ifrs(self):
        """IFRS has no ordinary-income concept, so the field stays null."""
        self.assertIsNone(self.result['ordinaryIncome'])

    def test_equity_extracts_via_jpigp_equity_ifrs(self):
        """equity comes from jpigp_cor:EquityIFRS for an IFRS filer."""
        self.assertEqual(self.result['equity'], 40000000000.0)

    def test_net_sales_extracts_for_ifrs_filer(self):
        """net_sales comes from the jpcrp IFRS revenue summary tag."""
        self.assertEqual(self.result['netSales'], 60000000000.0)

    def test_net_income_extracts_for_ifrs_filer(self):
        self.assertEqual(self.result['netIncome'], 6000000000.0)


if __name__ == '__main__':
    unittest.main()
