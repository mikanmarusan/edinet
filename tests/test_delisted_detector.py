#!/usr/bin/env python3
"""
Tests for lib/delisted_detector.py
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path so `lib.*` imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib import delisted_detector  # noqa: E402


class TestComputeDelisted(unittest.TestCase):
    """compute_delisted() set arithmetic"""

    def test_basic_diff(self):
        observed = {"1000", "2000", "3000", "4000"}
        jpx_listed = {"1000", "2000", "9999"}
        regional = set()
        self.assertEqual(
            delisted_detector.compute_delisted(observed, jpx_listed, regional),
            {"3000", "4000"},
        )

    def test_regional_is_excluded(self):
        # "3000" is observed and missing from JPX, but appears in regional skip.
        # It should NOT be flagged as delisted.
        observed = {"1000", "2000", "3000"}
        jpx_listed = {"1000"}
        regional = {"3000"}
        self.assertEqual(
            delisted_detector.compute_delisted(observed, jpx_listed, regional),
            {"2000"},
        )

    def test_all_listed(self):
        observed = {"1000", "2000"}
        jpx_listed = {"1000", "2000", "3000"}
        self.assertEqual(
            delisted_detector.compute_delisted(observed, jpx_listed, set()),
            set(),
        )

    def test_empty_observed(self):
        self.assertEqual(
            delisted_detector.compute_delisted(set(), {"1000"}, set()),
            set(),
        )

    def test_alphanumeric_code(self):
        observed = {"259A", "275A", "1000"}
        jpx_listed = {"1000", "275A"}
        self.assertEqual(
            delisted_detector.compute_delisted(observed, jpx_listed, set()),
            {"259A"},
        )


class TestMergeDelistedYaml(unittest.TestCase):
    """merge_delisted_yaml() persistence logic"""

    def test_new_entry_gets_today_date(self):
        result = delisted_detector.merge_delisted_yaml(
            existing=None,
            current_delisted={"1234"},
            company_names={"1234": "株式会社テスト"},
            today="2026-04-11",
        )
        self.assertEqual(result["metadata"]["last_updated"], "2026-04-11")
        self.assertEqual(result["metadata"]["last_success"], "2026-04-11")
        self.assertEqual(result["metadata"]["consecutive_failures"], 0)
        self.assertIn("1234", result["delisted"])
        self.assertEqual(result["delisted"]["1234"]["name"], "株式会社テスト")
        self.assertEqual(result["delisted"]["1234"]["detectedDate"], "2026-04-11")
        self.assertIsNone(result["delisted"]["1234"]["reason"])

    def test_existing_entry_preserves_detected_date(self):
        existing = {
            "metadata": {
                "schema_version": 1,
                "last_updated": "2026-02-01",
                "last_success": "2026-02-01",
                "consecutive_failures": 0,
                "source": "https://example.com/data_j.xls",
            },
            "delisted": {
                "1234": {
                    "name": "旧名称",
                    "detectedDate": "2025-12-01",
                    "reason": None,
                }
            },
        }
        result = delisted_detector.merge_delisted_yaml(
            existing=existing,
            current_delisted={"1234"},
            company_names={"1234": "新名称"},
            today="2026-04-11",
        )
        self.assertEqual(result["delisted"]["1234"]["detectedDate"], "2025-12-01")
        # Name is refreshed, detectedDate is preserved.
        self.assertEqual(result["delisted"]["1234"]["name"], "新名称")

    def test_reinstated_entry_is_removed(self):
        existing = {
            "metadata": {},
            "delisted": {
                "1234": {"name": "A", "detectedDate": "2025-12-01", "reason": None},
                "5678": {"name": "B", "detectedDate": "2026-01-15", "reason": None},
            },
        }
        # "1234" is still delisted; "5678" has reappeared in JPX listing.
        result = delisted_detector.merge_delisted_yaml(
            existing=existing,
            current_delisted={"1234"},
            company_names={"1234": "A", "5678": "B"},
            today="2026-04-11",
        )
        self.assertIn("1234", result["delisted"])
        self.assertNotIn("5678", result["delisted"])

    def test_source_url_preserved_from_existing(self):
        existing = {"metadata": {"source": "https://custom.example/data.xls"}, "delisted": {}}
        result = delisted_detector.merge_delisted_yaml(
            existing=existing,
            current_delisted=set(),
            company_names={},
            today="2026-04-11",
        )
        self.assertEqual(result["metadata"]["source"], "https://custom.example/data.xls")

    def test_default_source_url_when_missing(self):
        result = delisted_detector.merge_delisted_yaml(
            existing=None,
            current_delisted=set(),
            company_names={},
            today="2026-04-11",
        )
        self.assertEqual(
            result["metadata"]["source"],
            delisted_detector.JPX_DATA_J_URL,
        )

    def test_consecutive_failures_reset_on_success(self):
        existing = {"metadata": {"consecutive_failures": 2}, "delisted": {}}
        result = delisted_detector.merge_delisted_yaml(
            existing=existing,
            current_delisted=set(),
            company_names={},
            today="2026-04-11",
        )
        self.assertEqual(result["metadata"]["consecutive_failures"], 0)


class TestRecordFailure(unittest.TestCase):
    """record_failure() increments counter and preserves delisted map"""

    def test_increments_counter_from_zero(self):
        existing = {"metadata": {"consecutive_failures": 0, "last_success": "2026-04-10"},
                    "delisted": {"1234": {"name": "A", "detectedDate": "2025-12-01", "reason": None}}}
        result, count = delisted_detector.record_failure(existing, "2026-04-11")
        self.assertEqual(count, 1)
        self.assertEqual(result["metadata"]["consecutive_failures"], 1)
        self.assertEqual(result["metadata"]["last_updated"], "2026-04-11")
        # last_success should be preserved.
        self.assertEqual(result["metadata"]["last_success"], "2026-04-10")
        # Delisted map preserved intact.
        self.assertIn("1234", result["delisted"])

    def test_increments_counter_from_two(self):
        existing = {"metadata": {"consecutive_failures": 2}, "delisted": {}}
        _, count = delisted_detector.record_failure(existing, "2026-04-11")
        self.assertEqual(count, 3)

    def test_missing_existing_starts_at_one(self):
        result, count = delisted_detector.record_failure(None, "2026-04-11")
        self.assertEqual(count, 1)
        self.assertEqual(result["metadata"]["consecutive_failures"], 1)


class TestLoadObservedSecsFromJsons(unittest.TestCase):
    """load_observed_secs_from_jsons() scanning logic"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="edinet_test_")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, filename: str, data):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_collects_all_observed_codes(self):
        self._write_json("2026-01-01.json", [
            {"secCode": "1000", "filerName": "Alpha"},
            {"secCode": "2000", "filerName": "Beta"},
        ])
        self._write_json("2026-02-01.json", [
            {"secCode": "3000", "filerName": "Gamma"},
        ])
        result = delisted_detector.load_observed_secs_from_jsons(self.tmpdir)
        self.assertEqual(set(result.keys()), {"1000", "2000", "3000"})

    def test_uses_most_recent_name(self):
        self._write_json("2026-01-01.json", [{"secCode": "1000", "filerName": "旧名"}])
        self._write_json("2026-03-01.json", [{"secCode": "1000", "filerName": "新名"}])
        result = delisted_detector.load_observed_secs_from_jsons(self.tmpdir)
        self.assertEqual(result["1000"], "新名")

    def test_ignores_non_list_json(self):
        self._write_json("2026-01-01.json", {"not": "a list"})
        self._write_json("2026-02-01.json", [{"secCode": "1000", "filerName": "OK"}])
        result = delisted_detector.load_observed_secs_from_jsons(self.tmpdir)
        self.assertEqual(set(result.keys()), {"1000"})

    def test_skips_entries_without_seccode(self):
        self._write_json("2026-01-01.json", [
            {"secCode": "1000", "filerName": "A"},
            {"filerName": "no code"},
            {"secCode": "", "filerName": "empty"},
        ])
        result = delisted_detector.load_observed_secs_from_jsons(self.tmpdir)
        self.assertEqual(set(result.keys()), {"1000"})

    def test_handles_malformed_json_gracefully(self):
        path = os.path.join(self.tmpdir, "2026-04-01.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ not valid json")
        self._write_json("2026-04-02.json", [{"secCode": "1000", "filerName": "OK"}])
        result = delisted_detector.load_observed_secs_from_jsons(self.tmpdir)
        self.assertEqual(set(result.keys()), {"1000"})


def _make_fake_sheet(rows):
    """Build a mock openpyxl read-only worksheet from a 2D Python list."""
    sheet = MagicMock()
    sheet.iter_rows.return_value = iter(rows)
    return sheet


class TestLoadJpxListedSet(unittest.TestCase):
    """load_jpx_listed_set() handles openpyxl cell types correctly"""

    def setUp(self):
        # Create a dummy file so os.path.exists passes.
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        self.tmpfile.write(b"fake")
        self.tmpfile.close()

    def tearDown(self):
        os.unlink(self.tmpfile.name)

    def _run_with_rows(self, rows):
        sheet = _make_fake_sheet(rows)
        book = MagicMock()
        book.worksheets = [sheet]
        with patch.object(delisted_detector.openpyxl, "load_workbook", return_value=book):
            return delisted_detector.load_jpx_listed_set(self.tmpfile.name)

    def test_float_codes_zero_padded(self):
        rows = [
            ["日付", "コード", "銘柄名"],
            [20260401.0, 1301.0, "極洋"],
            [20260401.0, 7203.0, "トヨタ自動車"],
            [20260401.0, 9984.0, "ソフトバンクグループ"],
        ]
        result = self._run_with_rows(rows)
        self.assertEqual(result, {"1301", "7203", "9984"})

    def test_alphanumeric_codes_preserved(self):
        rows = [
            ["日付", "コード", "銘柄名"],
            [20260401.0, "259A", "Alpha Corp"],
            [20260401.0, 7203.0, "Toyota"],
        ]
        result = self._run_with_rows(rows)
        self.assertEqual(result, {"259A", "7203"})

    def test_empty_cells_are_skipped(self):
        rows = [
            ["日付", "コード", "銘柄名"],
            [20260401.0, 1301.0, "A"],
            [20260401.0, "", "empty"],
            [20260401.0, None, "none"],
        ]
        result = self._run_with_rows(rows)
        self.assertEqual(result, {"1301"})

    def test_missing_code_column_raises(self):
        rows = [
            ["日付", "銘柄名", "市場"],
            [20260401.0, "Alpha", "プライム"],
        ]
        with self.assertRaises(ValueError):
            self._run_with_rows(rows)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            delisted_detector.load_jpx_listed_set("/does/not/exist.xls")


class TestLoadRegionalSkipSet(unittest.TestCase):
    """load_regional_skip_set() reads existing config file"""

    def test_loads_actual_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "stock_exchange_mapping.yml"
        )
        skip_set = delisted_detector.load_regional_skip_set(config_path)
        # The real config has Nagoya / Fukuoka / Sapporo codes, at minimum.
        self.assertGreater(len(skip_set), 10)
        # Sanity: a known Nagoya code exists in the mapping.
        self.assertIn("1738", skip_set)

    def test_missing_file_returns_empty(self):
        result = delisted_detector.load_regional_skip_set("/nonexistent/path.yml")
        self.assertEqual(result, set())


if __name__ == "__main__":
    unittest.main()
