"""
Tests for EPS sourcing (issue #183).

EPS must come from XBRL via _extract_eps (or be null), and must never be
fabricated from the operatingIncome * 0.7 approximation, because a fabricated
EPS corrupts the self-computed PER.
"""

import unittest

from defusedxml.ElementTree import fromstring as defused_fromstring

from lib.xbrl_parser import MetricsCalculator, XBRLParser


# Minimal XBRL (default 2024-11-01 taxonomy) carrying a basic EPS and no shares.
EPS_DOC = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    b'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor">'
    b'<xbrli:context id="CurrentYearDuration">'
    b'<xbrli:period>'
    b'<xbrli:startDate>2024-04-01</xbrli:startDate>'
    b'<xbrli:endDate>2025-03-31</xbrli:endDate>'
    b'</xbrli:period>'
    b'</xbrli:context>'
    b'<jppfs_cor:BasicEarningsPerShare contextRef="CurrentYearDuration">123.45</jppfs_cor:BasicEarningsPerShare>'
    b'</xbrli:xbrl>'
)


class TestEpsApproximationRemoved(unittest.TestCase):
    """_calculate_eps must never fabricate EPS from operatingIncome * 0.7."""

    def test_no_operating_income_approximation_when_shares_present(self):
        """Net income missing but operating income + shares present: returns None,
        not operatingIncome * 0.7 / shares."""
        data = {
            'netIncome': None,
            'operatingIncome': 1_000_000_000,
            'outstandingShares': 1_000_000,
        }
        self.assertIsNone(MetricsCalculator._calculate_eps(data))

    def test_uses_net_income_when_available(self):
        """The legitimate netIncome / shares path still works."""
        data = {
            'netIncome': 500_000_000,
            'operatingIncome': 1_000_000_000,
            'outstandingShares': 1_000_000,
        }
        self.assertEqual(MetricsCalculator._calculate_eps(data), 500.0)

    def test_derived_metrics_never_fabricates_eps(self):
        """With eps and shares both missing, the pipeline leaves eps None and
        never derives it from operating income."""
        data = {
            'eps': None,
            'operatingIncome': 1_000_000_000,
            'outstandingShares': None,
            'netSales': 2_000_000_000,
            'stockPrice': 1000,
        }
        result = MetricsCalculator.calculate_derived_metrics(data)
        self.assertIsNone(result['eps'])
        self.assertIsNone(result.get('per'))


class TestEpsSourcedFromExtract(unittest.TestCase):
    """eps is sourced from _extract_eps even when outstanding shares are absent."""

    def test_eps_from_xbrl_with_missing_shares(self):
        root = defused_fromstring(EPS_DOC)
        parser = XBRLParser()
        data = parser._build_financial_data_structure(
            root,
            sec_code='0000',
            filer_name='Test Co',
            doc_id='TESTDOC',
            period_end='2025-03-31',
            issued_date='2025-06-30',
            yahoo_data=None,
        )
        # EPS comes from the XBRL BasicEarningsPerShare element ...
        self.assertEqual(data['eps'], 123.45)
        # ... even though outstanding shares could not be extracted.
        self.assertIsNone(data['outstandingShares'])


if __name__ == '__main__':
    unittest.main()
