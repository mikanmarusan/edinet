#!/usr/bin/env python3
"""
Tests for the delisted-company annotation added to consolidate_documents.py
"""

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path so `bin.*` imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.consolidate_documents import DataConsolidator, load_delisted_map  # noqa: E402


class TestLoadDelistedMap(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="edinet_consolidate_test_")
        self.yaml_path = os.path.join(self.tmpdir, "delisted.yml")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, content: str):
        with open(self.yaml_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_empty_when_missing(self):
        self.assertEqual(load_delisted_map("/nonexistent/delisted.yml"), {})

    def test_loads_delisted_map(self):
        self._write(
            """metadata:
  schema_version: 1
delisted:
  "1234":
    name: テスト株式会社
    detectedDate: "2026-02-14"
    reason: null
  "5678":
    name: ABC
    detectedDate: "2026-03-01"
    reason: null
"""
        )
        result = load_delisted_map(self.yaml_path)
        self.assertIn("1234", result)
        self.assertEqual(result["1234"]["detectedDate"], "2026-02-14")
        self.assertIn("5678", result)

    def test_empty_delisted_key(self):
        self._write("metadata:\n  schema_version: 1\ndelisted: {}\n")
        self.assertEqual(load_delisted_map(self.yaml_path), {})

    def test_malformed_yaml(self):
        self._write("not: valid: [yaml")
        self.assertEqual(load_delisted_map(self.yaml_path), {})


class TestAnnotateDelisted(unittest.TestCase):
    """Verify _annotate_delisted attaches the right fields via consolidate_files()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="edinet_consolidate_test_")
        self.jsons_dir = os.path.join(self.tmpdir, "jsons")
        os.makedirs(self.jsons_dir)
        self.yaml_path = os.path.join(self.tmpdir, "delisted.yml")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, filename: str, companies):
        path = os.path.join(self.jsons_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(companies, f, ensure_ascii=False)

    def _write_yaml(self, body: str):
        with open(self.yaml_path, "w", encoding="utf-8") as f:
            f.write(body)

    def test_flags_delisted_company(self):
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        self._write_json(
            f"{today}.json",
            [
                {"secCode": "1234", "filerName": "Old Corp", "issuedDate": today},
                {"secCode": "5678", "filerName": "Active Corp", "issuedDate": today},
            ],
        )
        self._write_yaml(
            """metadata:
  schema_version: 1
delisted:
  "1234":
    name: Old Corp
    detectedDate: "2026-02-14"
    reason: null
"""
        )

        consolidator = DataConsolidator(self.jsons_dir, delisted_yaml_path=self.yaml_path)
        results = consolidator.consolidate_files()

        by_code = {c["secCode"]: c for c in results}
        self.assertTrue(by_code["1234"]["isDelisted"])
        self.assertEqual(by_code["1234"]["delistedDate"], "2026-02-14")
        self.assertFalse(by_code["5678"]["isDelisted"])
        self.assertIsNone(by_code["5678"]["delistedDate"])

    def test_no_yaml_path_skips_annotation(self):
        """When delisted_yaml_path is None, consolidate should not touch isDelisted."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        self._write_json(
            f"{today}.json",
            [{"secCode": "1234", "filerName": "Corp", "issuedDate": today}],
        )

        consolidator = DataConsolidator(self.jsons_dir, delisted_yaml_path=None)
        results = consolidator.consolidate_files()

        self.assertNotIn("isDelisted", results[0])
        self.assertNotIn("delistedDate", results[0])

    def test_missing_yaml_file_defaults_to_false(self):
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        self._write_json(
            f"{today}.json",
            [{"secCode": "1234", "filerName": "Corp", "issuedDate": today}],
        )

        missing_yaml = os.path.join(self.tmpdir, "nonexistent.yml")
        consolidator = DataConsolidator(self.jsons_dir, delisted_yaml_path=missing_yaml)
        results = consolidator.consolidate_files()

        self.assertFalse(results[0]["isDelisted"])
        self.assertIsNone(results[0]["delistedDate"])


if __name__ == "__main__":
    unittest.main()
