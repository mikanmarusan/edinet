"""
Positive extraction test for XBRL-sourced financial-statement fields (issue #183).

The other suites use stripped XBRL that omits these tags, so they would stay
green even if an _extract_* method silently broke. This fixture carries real
financial-statement elements and asserts they populate non-null, guarding
against the silent null-out the Yahoo->XBRL cutover could otherwise hide.
"""

import unittest

from defusedxml.ElementTree import fromstring as defused_fromstring

from lib.xbrl_parser import XBRLParser


# A consolidated-free XBRL (default 2024-11-01 taxonomy) carrying the financial
# statement fields this PR moves to XBRL sourcing. Values are synthetic.
FULL_DOC = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    b'xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor" '
    b'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor">'
    b'<xbrli:context id="CurrentYearDuration">'
    b'<xbrli:period><xbrli:startDate>2024-04-01</xbrli:startDate>'
    b'<xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period>'
    b'</xbrli:context>'
    b'<xbrli:context id="CurrentYearInstant">'
    b'<xbrli:period><xbrli:instant>2025-03-31</xbrli:instant></xbrli:period>'
    b'</xbrli:context>'
    b'<jpcrp_cor:DescriptionOfBusinessTextBlock contextRef="CurrentYearDuration">'
    b'Test manufacturing business.</jpcrp_cor:DescriptionOfBusinessTextBlock>'
    b'<jppfs_cor:NetSales contextRef="CurrentYearDuration">50000000000</jppfs_cor:NetSales>'
    b'<jppfs_cor:OperatingIncome contextRef="CurrentYearDuration">5000000000</jppfs_cor:OperatingIncome>'
    b'<jppfs_cor:DepreciationAndAmortization contextRef="CurrentYearDuration">1000000000</jppfs_cor:DepreciationAndAmortization>'
    b'<jppfs_cor:ProfitLoss contextRef="CurrentYearDuration">3000000000</jppfs_cor:ProfitLoss>'
    b'<jppfs_cor:BasicEarningsPerShare contextRef="CurrentYearDuration">250.5</jppfs_cor:BasicEarningsPerShare>'
    b'<jppfs_cor:NumberOfEmployees contextRef="CurrentYearInstant">1200</jppfs_cor:NumberOfEmployees>'
    b'<jppfs_cor:BookValuePerShare contextRef="CurrentYearInstant">1500</jppfs_cor:BookValuePerShare>'
    b'<jppfs_cor:NumberOfIssuedShares contextRef="CurrentYearInstant">10000000</jppfs_cor:NumberOfIssuedShares>'
    b'</xbrli:xbrl>'
)


class TestXbrlFieldSourcing(unittest.TestCase):
    """Financial-statement fields populate from XBRL, with no yahoo_data."""

    def test_fields_populate_from_xbrl(self):
        root = defused_fromstring(FULL_DOC)
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
        self.assertEqual(data['netSales'], 50000000000)
        self.assertEqual(data['operatingIncome'], 5000000000)
        self.assertEqual(data['depreciation'], 1000000000)
        self.assertEqual(data['netIncome'], 3000000000)
        self.assertEqual(data['eps'], 250.5)
        self.assertEqual(data['employees'], 1200)
        self.assertEqual(data['bps'], 1500)
        self.assertEqual(data['outstandingShares'], 10000000)
        self.assertIsNotNone(data['characteristic'])

    def test_market_fields_stay_none_without_fetcher(self):
        """stockPrice/ordinaryIncome/debt come from the market fetcher, so they
        are None when no yahoo_data is supplied - even though XBRL is rich."""
        root = defused_fromstring(FULL_DOC)
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
        self.assertIsNone(data['stockPrice'])
        self.assertIsNone(data['ordinaryIncome'])
        self.assertIsNone(data['debt'])


if __name__ == '__main__':
    unittest.main()
