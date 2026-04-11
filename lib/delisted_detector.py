#!/usr/bin/env python3
"""
Delisted Company Detector

Utilities for detecting delisted Japanese listed companies by comparing
the set of securities codes observed in EDINET daily fetches against the
JPX "東証上場銘柄一覧" (data_j.xls) snapshot.

The detection policy is:
    delisted = (observed_secs - regional_skip) - jpx_listed

where:
    observed_secs : secCodes ever seen in data/jsons/*.json (past EDINET data)
    jpx_listed    : secCodes currently present in JPX data_j.xls
    regional_skip : secCodes registered in config/stock_exchange_mapping.yml
                    (Nagoya / Fukuoka / Sapporo single-listed stocks which
                    are NOT included in the JPX Tokyo snapshot and must be
                    excluded to avoid false positives).
"""

import glob
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Set, Tuple

import xlrd
import yaml

# Allow running as a script from the project root or from lib/.
try:
    from lib.edinet_common import normalize_securities_code
except ImportError:  # pragma: no cover - fallback when lib is on sys.path directly
    from edinet_common import normalize_securities_code

logger = logging.getLogger(__name__)

JPX_DATA_J_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls"
)

# Candidate header names for the JPX "code" column.
_JPX_CODE_COLUMNS = ("コード", "Local Code", "コード（Code）")


def _normalize_raw_code(raw) -> str:
    """
    Convert a raw cell value (from xlrd or similar) into a securities code
    string. xlrd returns numeric-looking codes as floats (e.g., 1301.0), so
    we convert them to zero-padded 4-digit strings. Alphanumeric codes
    (e.g., 259A) are returned as plain strings.
    """
    if raw is None:
        return ""
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return ""
        return str(int(raw)).zfill(4)
    if isinstance(raw, int):
        return str(raw).zfill(4)
    return str(raw).strip()


def load_jpx_listed_set(xls_path: str) -> Set[str]:
    """
    Load the set of currently-listed securities codes from the JPX snapshot.

    Uses xlrd directly (not pandas) because pandas 2.x requires xlrd>=2.0,
    but xlrd 2.x dropped .xls support. The `data_j.xls` file JPX publishes
    is an actual legacy .xls, so we pin xlrd==1.2.0 and call it directly.

    Args:
        xls_path: Local path to the downloaded data_j.xls file.

    Returns:
        Set of normalized securities codes currently listed on JPX (TSE).

    Raises:
        FileNotFoundError: If xls_path does not exist.
        ValueError: If the code column cannot be located in the sheet.
    """
    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"JPX listing file not found: {xls_path}")

    book = xlrd.open_workbook(xls_path)
    sheet = book.sheet_by_index(0)

    if sheet.nrows < 1:
        raise ValueError(f"JPX sheet is empty: {xls_path}")

    header = [sheet.cell_value(0, c) for c in range(sheet.ncols)]
    code_col_idx = None
    for idx, name in enumerate(header):
        if name in _JPX_CODE_COLUMNS:
            code_col_idx = idx
            break

    if code_col_idx is None:
        raise ValueError(
            f"Could not find a securities code column in {xls_path}. "
            f"Columns present: {header}"
        )

    listed: Set[str] = set()
    for row_idx in range(1, sheet.nrows):
        raw = sheet.cell_value(row_idx, code_col_idx)
        code = _normalize_raw_code(raw)
        if not code:
            continue
        listed.add(normalize_securities_code(code))

    logger.info(
        "Loaded %d listed securities codes from JPX snapshot: %s",
        len(listed),
        xls_path,
    )
    return listed


def load_regional_skip_set(config_path: str) -> Set[str]:
    """
    Load the exclusion set from config/stock_exchange_mapping.yml.

    Codes registered in this file denote regional-exchange single-listed stocks
    (Nagoya / Fukuoka / Sapporo) that are NOT represented in JPX data_j.xls.
    They must be skipped during delisted detection to avoid being flagged as
    delisted.

    Args:
        config_path: Path to config/stock_exchange_mapping.yml

    Returns:
        Set of securities codes to exclude from delisted judgement.
        Returns an empty set if the file is missing or unreadable.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Could not load regional skip mapping %s: %s", config_path, e)
        return set()

    mapping = data.get("stock_exchanges", {}) or {}
    return {str(code) for code in mapping.keys()}


def load_observed_secs_from_jsons(jsons_dir: str) -> Dict[str, str]:
    """
    Scan data/jsons/*.json files to collect every secCode ever observed and
    the most recently seen company name for that code.

    Recency is determined by the daily JSON filename (YYYY-MM-DD.json).
    Files whose names do not match that format are still processed but their
    entries never "win" the recency comparison.

    Args:
        jsons_dir: Directory containing daily JSON files.

    Returns:
        Mapping of {secCode: filerName} based on the most recently observed
        occurrence of each code.
    """
    observed: Dict[str, Tuple[str, str]] = {}

    pattern = os.path.join(jsons_dir, "*.json")
    json_files = sorted(glob.glob(pattern))

    for json_file in json_files:
        filename = os.path.basename(json_file)
        date_str = filename[:-5] if filename.endswith(".json") else ""

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read %s: %s", json_file, e)
            continue

        if not isinstance(data, list):
            continue

        for company in data:
            if not isinstance(company, dict):
                continue
            raw_code = company.get("secCode")
            if not raw_code:
                continue
            sec_code = normalize_securities_code(str(raw_code))
            if not sec_code:
                continue
            name = company.get("filerName") or ""
            previous = observed.get(sec_code)
            if previous is None or date_str > previous[0]:
                observed[sec_code] = (date_str, name)

    logger.info(
        "Observed %d distinct securities codes across %d JSON files",
        len(observed),
        len(json_files),
    )
    return {code: name for code, (_date, name) in observed.items()}


def compute_delisted(
    observed_secs: Set[str],
    jpx_listed: Set[str],
    regional_skip: Set[str],
) -> Set[str]:
    """
    Compute the set of currently-delisted securities codes.

        delisted = (observed_secs - regional_skip) - jpx_listed

    Args:
        observed_secs: All secCodes ever observed in EDINET daily fetches.
        jpx_listed:    secCodes currently listed on JPX (from data_j.xls).
        regional_skip: secCodes to exclude (regional single-listed stocks).

    Returns:
        Set of secCodes considered delisted.
    """
    candidates = observed_secs - regional_skip
    return candidates - jpx_listed


def merge_delisted_yaml(
    existing: Optional[dict],
    current_delisted: Set[str],
    company_names: Dict[str, str],
    today: str,
    source_url: str = JPX_DATA_J_URL,
) -> dict:
    """
    Merge a freshly computed delisted set into the existing YAML structure,
    preserving ``detectedDate`` of codes that were already known to be
    delisted, removing codes that have returned to the JPX listing, and
    refreshing metadata.

    Args:
        existing: Previous delisted_companies.yml content (may be None/empty).
        current_delisted: Full set of currently-delisted secCodes.
        company_names: Mapping {secCode: filerName} for naming new entries.
        today: Today's date in YYYY-MM-DD format. Used as ``detectedDate``
               for newly discovered codes and as ``last_updated`` /
               ``last_success`` in metadata.
        source_url: Source attribution stored in metadata.

    Returns:
        A new dict ready to be dumped to YAML with the shape::

            metadata:
              schema_version: 1
              last_updated: "YYYY-MM-DD"
              last_success: "YYYY-MM-DD"
              consecutive_failures: 0
              source: "https://..."
            delisted:
              "1234":
                name: "..."
                detectedDate: "YYYY-MM-DD"
                reason: null
    """
    existing = existing or {}
    existing_meta = (existing.get("metadata") or {}) if isinstance(existing, dict) else {}
    existing_delisted = (existing.get("delisted") or {}) if isinstance(existing, dict) else {}

    merged: Dict[str, dict] = {}

    # Retain entries that are still delisted; drop the ones that were reinstated.
    for code, info in existing_delisted.items():
        code_str = str(code)
        if code_str not in current_delisted:
            logger.info("Reinstated (reappeared in JPX listing): %s", code_str)
            continue
        entry = dict(info) if isinstance(info, dict) else {}
        # Refresh the display name if we have a newer observation.
        new_name = company_names.get(code_str)
        if new_name:
            entry["name"] = new_name
        entry.setdefault("detectedDate", today)
        entry.setdefault("reason", None)
        merged[code_str] = entry

    # Add newly detected codes.
    for code in sorted(current_delisted):
        if code in merged:
            continue
        logger.info("Newly detected delisted: %s (%s)", code, company_names.get(code, ""))
        merged[code] = {
            "name": company_names.get(code, ""),
            "detectedDate": today,
            "reason": None,
        }

    result = {
        "metadata": {
            "schema_version": 1,
            "last_updated": today,
            "last_success": today,
            "consecutive_failures": 0,
            "source": existing_meta.get("source") or source_url,
        },
        "delisted": dict(sorted(merged.items())),
    }
    return result


def record_failure(existing: Optional[dict], today: str) -> Tuple[dict, int]:
    """
    Build a YAML dict reflecting a failed JPX fetch.

    Increments ``metadata.consecutive_failures``, updates ``last_updated``,
    and preserves the existing ``delisted`` map intact. ``last_success`` is
    preserved from the previous run.

    Returns:
        (new_yaml_dict, new_consecutive_failures_count)
    """
    existing = existing or {}
    existing_meta = (existing.get("metadata") or {}) if isinstance(existing, dict) else {}
    existing_delisted = (existing.get("delisted") or {}) if isinstance(existing, dict) else {}

    prev_failures = int(existing_meta.get("consecutive_failures") or 0)
    new_failures = prev_failures + 1

    result = {
        "metadata": {
            "schema_version": 1,
            "last_updated": today,
            "last_success": existing_meta.get("last_success"),
            "consecutive_failures": new_failures,
            "source": existing_meta.get("source") or JPX_DATA_J_URL,
        },
        "delisted": dict(sorted((str(k), v) for k, v in existing_delisted.items())),
    }
    return result, new_failures


def today_iso() -> str:
    """Return today's date in YYYY-MM-DD format (local time)."""
    return datetime.now().strftime("%Y-%m-%d")
