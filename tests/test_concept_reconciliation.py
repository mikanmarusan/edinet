"""
Tests for concept reconciliation (issue #184): ordinaryIncome extraction,
net_income attributable-to-owners preference, net interest-bearing debt, and
EV netting cash exactly once.

Fixtures are synthetic; the rules (not any specific filing's figure) are asserted.
"""

import unittest

from defusedxml.ElementTree import fromstring as defused_fromstring

from lib.xbrl_parser import XBRLParser, MetricsCalculator


NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor"'
)


def _doc(body_elements):
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<xbrli:xbrl {NS}>'
        '<xbrli:context id="CurrentYearDuration">'
        '<xbrli:period><xbrli:startDate>2024-04-01</xbrli:startDate>'
        '<xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period></xbrli:context>'
        '<xbrli:context id="CurrentYearInstant">'
        '<xbrli:period><xbrli:instant>2025-03-31</xbrli:instant></xbrli:period></xbrli:context>'
    )
    return (head + body_elements + '</xbrli:xbrl>').encode('utf-8')


class TestOrdinaryIncome(unittest.TestCase):
    def test_extracted_from_xbrl(self):
        doc = _doc('<jppfs_cor:OrdinaryIncome contextRef="CurrentYearDuration">7500000000</jppfs_cor:OrdinaryIncome>')
        parser = XBRLParser()
        self.assertEqual(parser._extract_ordinary_income(defused_fromstring(doc)), 7500000000)

    def test_none_for_ifrs_filer_without_ordinary_income(self):
        # No ordinary-income concept present (as for an IFRS filer).
        doc = _doc('<jppfs_cor:NetSales contextRef="CurrentYearDuration">50000000000</jppfs_cor:NetSales>')
        parser = XBRLParser()
        self.assertIsNone(parser._extract_ordinary_income(defused_fromstring(doc)))


class TestNetIncomeAttributable(unittest.TestCase):
    def test_prefers_attributable_over_bare_profit_loss(self):
        # Bare ProfitLoss (total, incl. non-controlling interests) is larger;
        # the attributable-to-owners value must win.
        doc = _doc(
            '<jppfs_cor:ProfitLoss contextRef="CurrentYearDuration">136441000000</jppfs_cor:ProfitLoss>'
            '<jppfs_cor:ProfitLossAttributableToOwnersOfParent contextRef="CurrentYearDuration">'
            '132986000000</jppfs_cor:ProfitLossAttributableToOwnersOfParent>'
        )
        parser = XBRLParser()
        value = parser._extract_net_income(defused_fromstring(doc))
        self.assertEqual(value, 132986000000)

    def test_net_income_loss_preferred_over_bare_profit_loss(self):
        # NetIncomeLoss is ordered above bare ProfitLoss; it must win.
        doc = _doc(
            '<jppfs_cor:ProfitLoss contextRef="CurrentYearDuration">9000000000</jppfs_cor:ProfitLoss>'
            '<jppfs_cor:NetIncomeLoss contextRef="CurrentYearDuration">8000000000</jppfs_cor:NetIncomeLoss>'
        )
        parser = XBRLParser()
        self.assertEqual(parser._extract_net_income(defused_fromstring(doc)), 8000000000)

    def test_falls_back_to_bare_profit_loss(self):
        doc = _doc('<jppfs_cor:ProfitLoss contextRef="CurrentYearDuration">5000000000</jppfs_cor:ProfitLoss>')
        parser = XBRLParser()
        self.assertEqual(parser._extract_net_income(defused_fromstring(doc)), 5000000000)


class TestNetInterestBearingDebt(unittest.TestCase):
    DEBT_DOC = _doc(
        '<jppfs_cor:ShortTermLoansPayable contextRef="CurrentYearInstant">1000</jppfs_cor:ShortTermLoansPayable>'
        '<jppfs_cor:CurrentPortionOfLongTermLoansPayable contextRef="CurrentYearInstant">500</jppfs_cor:CurrentPortionOfLongTermLoansPayable>'
        '<jppfs_cor:LongTermLoansPayable contextRef="CurrentYearInstant">3000</jppfs_cor:LongTermLoansPayable>'
        '<jppfs_cor:BondsPayable contextRef="CurrentYearInstant">2000</jppfs_cor:BondsPayable>'
        '<jppfs_cor:LeaseObligationsCL contextRef="CurrentYearInstant">100</jppfs_cor:LeaseObligationsCL>'
        '<jppfs_cor:LeaseObligationsNCL contextRef="CurrentYearInstant">400</jppfs_cor:LeaseObligationsNCL>'
        '<jppfs_cor:CashAndCashEquivalents contextRef="CurrentYearInstant">1500</jppfs_cor:CashAndCashEquivalents>'
    )

    def test_net_debt_is_components_minus_cash(self):
        # gross = 1000+500+3000+2000+100+400 = 7000; net = 7000 - 1500 = 5500
        parser = XBRLParser()
        self.assertEqual(parser._extract_debt(defused_fromstring(self.DEBT_DOC)), 5500)

    def test_none_when_no_interest_bearing_component(self):
        doc = _doc('<jppfs_cor:CashAndCashEquivalents contextRef="CurrentYearInstant">1500</jppfs_cor:CashAndCashEquivalents>')
        parser = XBRLParser()
        self.assertIsNone(parser._extract_debt(defused_fromstring(doc)))


class TestEvNetsCashOnce(unittest.TestCase):
    def test_ev_adds_net_debt_without_subtracting_cash_again(self):
        # debt is already net of cash; EV = marketCap + debt, cash NOT re-subtracted.
        data = {
            'marketCapitalization': 10000,
            'debt': 5500,      # already net of the 1500 cash
            'cash': 1500,
        }
        result = MetricsCalculator.calculate_derived_metrics(data)
        self.assertEqual(result['ev'], 15500)  # 10000 + 5500, not 15500 - 1500


if __name__ == '__main__':
    unittest.main()
