"""
Tests for the docURL field (issue #186): EDINET web-viewer link with docID
alphanumeric validation.
"""

import re
import unittest

from defusedxml.ElementTree import fromstring as defused_fromstring

from lib.xbrl_parser import XBRLParser


MIN_DOC = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"></xbrli:xbrl>'
)


class TestDocURL(unittest.TestCase):
    def _build(self, doc_id):
        parser = XBRLParser()
        root = defused_fromstring(MIN_DOC)
        return parser._build_financial_data_structure(
            root,
            sec_code='0000',
            filer_name='Test Co',
            doc_id=doc_id,
            period_end='2025-03-31',
            issued_date='2025-06-30',
            yahoo_data=None,
        )

    def test_docurl_format_for_valid_docid(self):
        data = self._build('S100YE8K')
        self.assertEqual(
            data['docURL'],
            'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YE8K',
        )

    def test_invalid_docid_nulls_both_urls(self):
        # An invalid docID nulls both the web-viewer and the PDF link (consistent).
        for bad in ['S100 YE8K', 'S100/YE8K', 'S100?x=1', 'S100<script>', '']:
            with self.subTest(doc_id=bad):
                data = self._build(bad)
                self.assertIsNone(data['docURL'])
                self.assertIsNone(data['docPdfURL'])

    def test_docid_validation_pattern(self):
        self.assertIsNotNone(re.match(r'^[A-Za-z0-9]+$', 'S100YE8K'))
        self.assertIsNone(re.match(r'^[A-Za-z0-9]+$', 'S100?x=1'))


class TestDocURLConsolidationPassthrough(unittest.TestCase):
    """docURL survives consolidation unchanged (no field whitelist)."""

    def test_docurl_passes_through_latest_entry(self):
        from bin.consolidate_documents import DataConsolidator
        consolidator = DataConsolidator('.')
        entries = [
            {'secCode': '0000', 'issuedDate': '2025-05-01',
             'docURL': 'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?OLD'},
            {'secCode': '0000', 'issuedDate': '2025-06-30',
             'docURL': 'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YE8K'},
        ]
        latest = consolidator._get_latest_entry(entries)
        self.assertEqual(
            latest['docURL'],
            'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YE8K',
        )


if __name__ == '__main__':
    unittest.main()
