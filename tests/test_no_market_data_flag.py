"""Tests for the --no-market-data flag of fetch_edinet_financial_documents.

The flag must skip the market-data (Yahoo) fetch entirely: get_financial_data
is not called, and the parser receives yahoo_data=None so the market fields and
their derived metrics are left null. Without the flag, the fetch runs as before.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path so the script's `from lib...` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BIN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin",
    "fetch_edinet_financial_documents.py",
)


def _load_fetch_module():
    """Import the bin script as a module so its main() can be driven directly."""
    spec = importlib.util.spec_from_file_location("fetch_edinet_main", _BIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNoMarketDataFlag(unittest.TestCase):
    """Verify the --no-market-data flag controls whether Yahoo is fetched."""

    def setUp(self):
        self.fetch = _load_fetch_module()
        self.tmpdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_tmp_no_market_data"
        )
        os.makedirs(self.tmpdir, exist_ok=True)

    def tearDown(self):
        out = os.path.join(self.tmpdir, "2023-06-22.json")
        if os.path.exists(out):
            os.remove(out)
        if os.path.isdir(self.tmpdir):
            os.rmdir(self.tmpdir)

    def _run_main(self, extra_args):
        """Drive main() with a single fake document and mocked dependencies."""
        argv = [
            "fetch_edinet_financial_documents.py",
            "--date", "2023-06-22",
            "--outputdir", self.tmpdir,
            "--api-key", "dummy-key-1234567890",
        ] + extra_args

        fake_client = MagicMock()
        fake_client.get_documents.return_value = [
            {"docID": "S100TEST", "secCode": "9999", "filerName": "テスト株式会社",
             "periodEnd": "2023-03-31"}
        ]
        fake_client.download_document.return_value = b"dummy-xbrl-bytes"

        with patch.object(sys, "argv", argv), \
                patch.object(self.fetch, "EdinetClient", return_value=fake_client), \
                patch.object(self.fetch, "XBRLParser") as mock_parser_cls, \
                patch.object(self.fetch, "get_financial_data") as mock_get_fin:
            mock_parser_cls.return_value.parse_financial_data.return_value = {
                "secCode": "9999", "stockPrice": None, "marketCapitalization": None,
            }
            mock_get_fin.return_value = {"stockPrice": 1000.0,
                                         "marketCapitalization": 9_000_000_000}
            self.fetch.main()
            return mock_get_fin, mock_parser_cls.return_value.parse_financial_data

    def test_flag_skips_yahoo_fetch(self):
        """With --no-market-data, get_financial_data is never called and the
        parser receives yahoo_data=None."""
        mock_get_fin, mock_parse = self._run_main(["--no-market-data"])
        mock_get_fin.assert_not_called()
        # yahoo_data is the 7th positional arg of parse_financial_data.
        call = mock_parse.call_args
        yahoo_data = call.args[6] if len(call.args) > 6 else call.kwargs.get("yahoo_data")
        self.assertIsNone(yahoo_data)

    def test_without_flag_fetches_yahoo(self):
        """Without the flag, get_financial_data is called as before."""
        mock_get_fin, _ = self._run_main([])
        mock_get_fin.assert_called_once()


if __name__ == "__main__":
    unittest.main()
