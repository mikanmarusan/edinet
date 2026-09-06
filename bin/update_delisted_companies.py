#!/usr/bin/env python3
"""
Update data/delisted_companies.yml by detecting newly delisted companies.

Fetches JPX "東証上場銘柄一覧" (data_j.xlsx), compares it with every secCode
ever observed in data/jsons/*.json, excludes regional-exchange single-listed
stocks (stock_exchange_mapping.yml), and writes the resulting delisted set
to data/delisted_companies.yml.

Fail-safe with escalation on JPX fetch failure:
    1 consecutive failure  -> warning to stderr, exit 0
    2 consecutive failures -> warning + GitHub Actions step summary, exit 0
    3 consecutive failures -> exit 1 (fails the workflow step)

Usage:
    python bin/update_delisted_companies.py \
        --jsonsdir data/jsons \
        --mapping config/stock_exchange_mapping.yml \
        --output data/delisted_companies.yml
"""

import argparse
import logging
import os
import sys
import tempfile
from urllib.parse import urlparse

import requests
import yaml

# Allow running the script directly (bin/update_delisted_companies.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.delisted_detector import (
    JPX_DATA_J_URL,
    compute_delisted,
    load_jpx_listed_set,
    load_observed_secs_from_jsons,
    load_regional_skip_set,
    merge_delisted_yaml,
    record_failure,
    today_iso,
)
from lib.edinet_common import ensure_output_directory, setup_logging

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "edinet-delisted-detector/0.1 (+https://github.com/mikanmarusan/edinet)"
)
DEFAULT_TIMEOUT = 60  # seconds
DOWNLOAD_RETRIES = 2


def download_jpx_xls(url: str, user_agent: str = DEFAULT_USER_AGENT) -> str:
    """
    Download the JPX data_j.xlsx file to a temporary path.

    Retries up to DOWNLOAD_RETRIES times on transient failures.

    Returns:
        Path to a temporary file containing the downloaded bytes.

    Raises:
        RuntimeError: If the download fails after all retries.
    """
    last_exc = None
    for attempt in range(1, DOWNLOAD_RETRIES + 2):
        try:
            logger.info("Downloading JPX listing from %s (attempt %d)", url, attempt)
            response = requests.get(
                url,
                headers={"User-Agent": user_agent},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            if not response.content:
                raise RuntimeError("Empty response body")

            # openpyxl validates the file by its extension, not its content,
            # so the temp file suffix must match the real .xlsx format or
            # load_jpx_listed_set() raises InvalidFileException. Derive the
            # suffix from the URL's path (not the raw URL, so a query string
            # or fragment on a custom --source-url is never folded into the
            # suffix), falling back to .xlsx when the path has no extension.
            suffix = os.path.splitext(urlparse(url).path)[1] or ".xlsx"
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.write(response.content)
            tmp.close()
            logger.info(
                "Downloaded %d bytes (Content-Type=%s) to %s",
                len(response.content),
                response.headers.get("Content-Type", "unknown"),
                tmp.name,
            )
            return tmp.name
        except Exception as e:  # noqa: BLE001 - we want to retry any error
            last_exc = e
            logger.warning("JPX download attempt %d failed: %s", attempt, e)
    raise RuntimeError(f"Failed to download JPX listing after {DOWNLOAD_RETRIES + 1} attempts: {last_exc}")


def load_existing_yaml(output_path: str) -> dict:
    """Load the current delisted_companies.yml, returning {} if absent."""
    if not os.path.exists(output_path):
        return {}
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Could not parse existing %s: %s", output_path, e)
        return {}


def save_yaml(output_path: str, data: dict) -> None:
    """Write the YAML document, ensuring the output directory exists."""
    ensure_output_directory(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            "# 上場廃止企業リスト (auto-generated)\n"
            "# 検出方法: JPX data_j.xlsx にない、かつ stock_exchange_mapping.yml 未登録、\n"
            "#           かつ data/jsons/ で過去に観測された secCode\n"
            "# 自動更新スクリプト: bin/update_delisted_companies.py\n"
        )
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def write_step_summary(message: str) -> None:
    """Append a message to $GITHUB_STEP_SUMMARY, if that env var is set."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except OSError as e:
        logger.warning("Could not write GitHub step summary: %s", e)


def run(
    jsons_dir: str,
    mapping_path: str,
    output_path: str,
    max_consecutive_failures: int,
    source_url: str,
) -> int:
    """
    Execute the update. Returns the process exit code.
    """
    existing = load_existing_yaml(output_path)
    today = today_iso()

    # --- 1) Download JPX file ---
    try:
        xls_path = download_jpx_xls(source_url)
    except Exception as e:  # noqa: BLE001
        logger.error("JPX download failed: %s", e)
        failed_doc, count = record_failure(existing, today)
        save_yaml(output_path, failed_doc)

        message = (
            f":warning: delisted-companies update failed ({count} consecutive). "
            f"Reason: {e}"
        )
        if count >= max_consecutive_failures:
            logger.error(
                "%d consecutive failures reached (threshold=%d). Failing step.",
                count,
                max_consecutive_failures,
            )
            write_step_summary(message + " **Failing the step.**")
            return 1
        if count >= 2:
            logger.warning("%d consecutive failures. Writing GitHub step summary.", count)
            write_step_summary(message)
        else:
            logger.warning("%d consecutive failure (soft warning).", count)
        return 0

    try:
        # --- 2) Parse JPX listing ---
        jpx_listed = load_jpx_listed_set(xls_path)

        # --- 3) Build regional exclusion set ---
        regional_skip = load_regional_skip_set(mapping_path)

        # --- 4) Collect observed secCodes from daily JSONs ---
        observed_map = load_observed_secs_from_jsons(jsons_dir)
        observed_set = set(observed_map.keys())

        # --- 5) Compute the current delisted set ---
        current_delisted = compute_delisted(observed_set, jpx_listed, regional_skip)
        logger.info(
            "Detection stats: observed=%d, jpx_listed=%d, regional_skip=%d, delisted=%d",
            len(observed_set),
            len(jpx_listed),
            len(regional_skip),
            len(current_delisted),
        )

        # --- 6) Merge with existing yml (preserve detectedDate) ---
        merged = merge_delisted_yaml(
            existing=existing,
            current_delisted=current_delisted,
            company_names=observed_map,
            today=today,
            source_url=source_url,
        )

        # --- 7) Write ---
        save_yaml(output_path, merged)
        logger.info(
            "Wrote %s: %d delisted entries",
            output_path,
            len(merged.get("delisted", {})),
        )
        return 0
    finally:
        try:
            os.unlink(xls_path)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect delisted companies and update data/delisted_companies.yml",
    )
    parser.add_argument(
        "--jsonsdir",
        default="data/jsons",
        help="Directory containing daily EDINET JSON files (default: data/jsons)",
    )
    parser.add_argument(
        "--mapping",
        default="config/stock_exchange_mapping.yml",
        help="Regional exchange mapping YAML file (used as exclusion list)",
    )
    parser.add_argument(
        "--output",
        default="data/delisted_companies.yml",
        help="Output YAML path (default: data/delisted_companies.yml)",
    )
    parser.add_argument(
        "--source-url",
        default=JPX_DATA_J_URL,
        help="JPX data_j.xlsx URL (default: official JPX URL)",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=3,
        help="Exit 1 after this many consecutive JPX fetch failures (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    setup_logging("update_delisted_companies", args.verbose)

    return run(
        jsons_dir=args.jsonsdir,
        mapping_path=args.mapping,
        output_path=args.output,
        max_consecutive_failures=args.max_consecutive_failures,
        source_url=args.source_url,
    )


if __name__ == "__main__":
    sys.exit(main())
