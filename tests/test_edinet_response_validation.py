"""Tests for EDINET API response validation and Subscription-Key redaction.

The EDINET browsing host answers API paths with an HTML error page under
HTTP 200, which slips past raise_for_status() and only fails later inside
response.json() as an opaque decoding error. validate_edinet_response() turns
that into a single log line naming the status, the content type and the URL,
with the API key redacted out of the URL first.

HTTP mocking uses stdlib unittest.mock, matching the idiom in
tests/test_data_scraper.py and tests/test_no_market_data_flag.py; no HTTP
mocking dependency is introduced.
"""

import importlib.util
import logging
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

# Add parent directory to path so the `from lib...` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.edinet_common import (  # noqa: E402
    EdinetAPIError,
    _redact_subscription_key,
    setup_logging,
    summarize_request_error,
    validate_edinet_response,
)

_BIN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin",
    "fetch_edinet_financial_documents.py",
)

# Sentinel API key. Any appearance of this string in a message is a leak.
FAKE_API_KEY = "sentinel-subscription-key-value"


def _load_fetch_module():
    """Import the bin script as a module so its client can be driven directly."""
    spec = importlib.util.spec_from_file_location("fetch_edinet_validation", _BIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_response(status_code=200, content_type="application/json", url=None,
                   headers=None, content=b"", json_data=None):
    """Build a stand-in requests.Response with the attributes the code reads."""
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.url = url if url is not None else (
        "https://api.edinet-fsa.go.jp/api/v2/documents.json"
        f"?date=2026-08-29&type=2&Subscription-Key={FAKE_API_KEY}"
    )
    response_headers = {}
    if content_type is not None:
        response_headers["Content-Type"] = content_type
    if headers:
        response_headers.update(headers)
    response.headers = response_headers
    response.content = content
    response.json.return_value = json_data if json_data is not None else {}
    response.raise_for_status.return_value = None
    return response


class TestRedactSubscriptionKey(unittest.TestCase):
    """The key travels as a query parameter, so it must never survive redaction."""

    def test_key_as_first_parameter(self):
        url = (f"https://api.edinet-fsa.go.jp/api/v2/documents.json"
               f"?Subscription-Key={FAKE_API_KEY}&date=2026-08-29&type=2")
        redacted = _redact_subscription_key(url)

        self.assertNotIn(FAKE_API_KEY, redacted)
        self.assertIn("date=2026-08-29", redacted)
        self.assertIn("type=2", redacted)

    def test_key_as_last_parameter(self):
        url = (f"https://api.edinet-fsa.go.jp/api/v2/documents.json"
               f"?date=2026-08-29&type=2&Subscription-Key={FAKE_API_KEY}")
        redacted = _redact_subscription_key(url)

        self.assertNotIn(FAKE_API_KEY, redacted)
        self.assertIn("date=2026-08-29", redacted)
        self.assertIn("type=2", redacted)

    def test_url_encoded_value(self):
        # A key containing characters that percent-encode in a query string.
        encoded_key = "abc%2Bdef%2Fghi%3D"
        url = (f"https://api.edinet-fsa.go.jp/api/v2/documents.json"
               f"?date=2026-08-29&Subscription-Key={encoded_key}&type=2")
        redacted = _redact_subscription_key(url)

        self.assertNotIn(encoded_key, redacted)
        self.assertNotIn("abc+def/ghi=", redacted)
        self.assertIn("date=2026-08-29", redacted)
        self.assertIn("type=2", redacted)

    def test_url_without_key(self):
        url = "https://api.edinet-fsa.go.jp/api/v2/documents.json?date=2026-08-29&type=2"
        redacted = _redact_subscription_key(url)

        self.assertIn("date=2026-08-29", redacted)
        self.assertIn("type=2", redacted)

    def test_url_without_query_string(self):
        url = "https://api.edinet-fsa.go.jp/api/v2/documents/S100ABCD"
        self.assertEqual(_redact_subscription_key(url), url)

    def test_parameter_is_redacted_not_dropped(self):
        # Pins the exact output, so an implementation that dropped the
        # parameter entirely (or returned an empty string) would still satisfy
        # every negative assertion above but fail here.
        url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?Subscription-Key={FAKE_API_KEY}"

        self.assertEqual(
            _redact_subscription_key(url),
            "https://api.edinet-fsa.go.jp/api/v2/documents.json?Subscription-Key=REDACTED"
        )

    def test_parameter_name_match_is_case_insensitive(self):
        # Deliberate over-redaction: a differently cased spelling must not slip
        # the key through. Without the case-folding comparison this fails.
        url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?subscription-key={FAKE_API_KEY}"

        self.assertNotIn(FAKE_API_KEY, _redact_subscription_key(url))

    def test_blank_valued_parameter_survives(self):
        # keep_blank_values=True: a valueless parameter must not be dropped by
        # the parse/re-serialize round trip.
        url = "https://api.edinet-fsa.go.jp/api/v2/documents.json?date=&type=2"

        self.assertIn("date=", _redact_subscription_key(url))
        self.assertIn("type=2", _redact_subscription_key(url))

    def test_repeated_key_parameter(self):
        url = (f"https://api.edinet-fsa.go.jp/api/v2/documents.json"
               f"?Subscription-Key={FAKE_API_KEY}&Subscription-Key=second-{FAKE_API_KEY}")
        redacted = _redact_subscription_key(url)

        self.assertNotIn(FAKE_API_KEY, redacted)


class TestValidateEdinetResponseListPath(unittest.TestCase):
    """The documents list endpoint allowlists application/json."""

    def test_html_under_http_200_raises_with_status_type_and_url(self):
        response = _make_response(status_code=200, content_type="text/html;charset=UTF-8")

        with self.assertRaises(EdinetAPIError) as ctx:
            validate_edinet_response(response, "Error fetching documents",
                                     expected_content_type="application/json")

        message = str(ctx.exception)
        self.assertIn("200", message)
        self.assertIn("text/html", message)
        self.assertIn("https://api.edinet-fsa.go.jp/api/v2/documents.json", message)
        self.assertIn("date=2026-08-29", message)
        # Negative assertion: the raw key must never reach the message.
        self.assertNotIn(FAKE_API_KEY, message)

    def test_json_under_http_200_passes(self):
        response = _make_response(status_code=200, content_type="application/json")

        validate_edinet_response(response, "Error fetching documents",
                                 expected_content_type="application/json")

    def test_json_with_charset_suffix_passes(self):
        response = _make_response(status_code=200,
                                  content_type="application/json; charset=utf-8")

        validate_edinet_response(response, "Error fetching documents",
                                 expected_content_type="application/json")

    def test_redirect_raises_naming_redacted_location(self):
        # raise_for_status() does not raise on 3xx and, with
        # allow_redirects=False, response.history stays empty, so the status
        # code is the only signal. This is the regression guard for that.
        location = (f"https://disclosure2.edinet-fsa.go.jp/api/v2/documents.json"
                    f"?date=2026-08-29&Subscription-Key={FAKE_API_KEY}")
        response = _make_response(status_code=302, content_type="text/html",
                                  headers={"Location": location})

        with self.assertRaises(EdinetAPIError) as ctx:
            validate_edinet_response(response, "Error fetching documents",
                                     expected_content_type="application/json")

        message = str(ctx.exception)
        self.assertIn("302", message)
        self.assertIn("disclosure2.edinet-fsa.go.jp", message)
        self.assertNotIn(FAKE_API_KEY, message)

    def test_redirect_without_location_header_still_raises(self):
        response = _make_response(status_code=301, content_type="text/html")

        with self.assertRaises(EdinetAPIError) as ctx:
            validate_edinet_response(response, "Error fetching documents",
                                     expected_content_type="application/json")

        self.assertIn("301", str(ctx.exception))
        self.assertNotIn(FAKE_API_KEY, str(ctx.exception))

    def test_missing_content_type_header_raises(self):
        response = _make_response(status_code=200, content_type=None)

        with self.assertRaises(EdinetAPIError):
            validate_edinet_response(response, "Error fetching documents",
                                     expected_content_type="application/json")


class TestValidateEdinetResponseDownloadPath(unittest.TestCase):
    """The download endpoint blocklists text/html and accepts everything else.

    The success-case content type of the ZIP could not be measured, so
    allowlisting an unverified value would risk rejecting a legitimate
    download. These cases pin that no such value was allowlisted.
    """

    def test_html_raises(self):
        response = _make_response(status_code=200, content_type="text/html; charset=UTF-8")

        with self.assertRaises(EdinetAPIError) as ctx:
            validate_edinet_response(response, "Error downloading document S100ABCD")

        message = str(ctx.exception)
        self.assertIn("200", message)
        self.assertIn("text/html", message)
        self.assertIn("S100ABCD", message)
        self.assertNotIn(FAKE_API_KEY, message)

    def test_octet_stream_passes(self):
        response = _make_response(status_code=200, content_type="application/octet-stream")

        validate_edinet_response(response, "Error downloading document S100ABCD")

    def test_zip_passes(self):
        response = _make_response(status_code=200, content_type="application/zip")

        validate_edinet_response(response, "Error downloading document S100ABCD")

    def test_redirect_raises(self):
        response = _make_response(status_code=302, content_type="application/zip",
                                  headers={"Location": "https://disclosure2.edinet-fsa.go.jp/"})

        with self.assertRaises(EdinetAPIError) as ctx:
            validate_edinet_response(response, "Error downloading document S100ABCD")

        self.assertIn("302", str(ctx.exception))


class TestSummarizeRequestError(unittest.TestCase):
    """str(a requests exception) embeds the request URL, so it is summarized."""

    def test_http_error_reports_status_and_reason(self):
        response = _make_response(status_code=503, content_type="text/html")
        response.reason = "Service Unavailable"
        error = requests.exceptions.HTTPError(
            f"503 Server Error: Service Unavailable for url: {response.url}"
        )
        error.response = response

        summary = summarize_request_error(error)

        self.assertEqual(summary, "HTTP 503 Service Unavailable")
        self.assertNotIn(FAKE_API_KEY, summary)

    def test_response_less_error_reports_the_class_name(self):
        error = requests.exceptions.ConnectTimeout(
            f"timed out for url: https://api.edinet-fsa.go.jp/?Subscription-Key={FAKE_API_KEY}"
        )

        summary = summarize_request_error(error)

        self.assertEqual(summary, "ConnectTimeout")
        self.assertNotIn(FAKE_API_KEY, summary)


class TestLoggingDoesNotLeakTheKey(unittest.TestCase):
    """urllib3 writes the full request target, query string included, to the log.

    It does so at DEBUG for every request and at WARNING when header parsing
    fails, so the guarantee is enforced by a handler-side redacting filter
    rather than by a log level.
    """

    def _run_setup_logging_in_tmpdir(self, emit):
        """Configure logging in a temp cwd, run `emit`, return the log text."""
        root = logging.getLogger()
        previous_root_level = root.level
        previous_root_handlers = list(root.handlers)
        previous_urllib3_level = logging.getLogger("urllib3").level
        # Prime the level so the assertion cannot be satisfied by leftover
        # state from an earlier test in the same process.
        logging.getLogger("urllib3").setLevel(logging.NOTSET)
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                setup_logging("test_response_validation", verbose=True)
                try:
                    emit()
                finally:
                    # Close before the temp directory is torn down.
                    for handler in list(root.handlers):
                        handler.close()
                log_path = os.path.join(
                    tmpdir,
                    f"test_response_validation_{datetime.now().strftime('%Y%m%d')}.log",
                )
                with open(log_path, encoding="utf-8") as log_file:
                    return log_file.read()
        finally:
            os.chdir(cwd)
            root.handlers = previous_root_handlers
            root.setLevel(previous_root_level)
            logging.getLogger("urllib3").setLevel(previous_urllib3_level)

    def test_urllib3_warning_record_reaches_the_log_without_the_key(self):
        # WARNING is above the urllib3 level clamp, so only the redacting
        # filter can keep the key out of this record.
        def emit():
            logging.getLogger("urllib3.connectionpool").warning(
                "Failed to parse headers (url=%s): boom",
                f"https://api.edinet-fsa.go.jp/api/v2/documents.json"
                f"?date=2026-08-29&Subscription-Key={FAKE_API_KEY}",
            )

        log_text = self._run_setup_logging_in_tmpdir(emit)

        self.assertIn("Failed to parse headers", log_text)
        self.assertIn("Subscription-Key=REDACTED", log_text)
        self.assertNotIn(FAKE_API_KEY, log_text)

    def test_application_record_without_the_key_is_untouched(self):
        def emit():
            logging.getLogger(__name__).info("Fetched 3 documents for 2026-08-29")

        log_text = self._run_setup_logging_in_tmpdir(emit)

        self.assertIn("Fetched 3 documents for 2026-08-29", log_text)

    def test_urllib3_per_request_debug_logging_is_clamped(self):
        def emit():
            self.assertGreater(logging.getLogger("urllib3").level, logging.DEBUG)

        self._run_setup_logging_in_tmpdir(emit)


class TestClientIntegration(unittest.TestCase):
    """The client wires the validator in and stops following redirects."""

    @classmethod
    def setUpClass(cls):
        # Loaded once: the bin script appends to sys.path unconditionally at
        # import time, so re-importing it per test would duplicate the entry.
        cls.fetch = _load_fetch_module()

    def test_get_documents_rejects_html_response(self):
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=200, content_type="text/html")

        with patch.object(client.session, "get", return_value=response):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.get_documents("2026-08-29")

        message = str(ctx.exception)
        self.assertIn("text/html", message)
        self.assertNotIn(FAKE_API_KEY, message)

    def test_get_documents_disables_redirects_and_returns_filtered_reports(self):
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        # The isinstance(data, dict) guard sits directly above this filter, so
        # the happy path is pinned here too: only docTypeCode 120 with a
        # secCode survives.
        response = _make_response(status_code=200, content_type="application/json",
                                  json_data={"results": [
                                      {"docTypeCode": "120", "secCode": "72030"},
                                      {"docTypeCode": "350", "secCode": "99840"},
                                      {"docTypeCode": "120", "secCode": None},
                                  ]})

        with patch.object(client.session, "get", return_value=response) as mock_get:
            reports = client.get_documents("2026-08-29")

        self.assertEqual(reports, [{"docTypeCode": "120", "secCode": "72030"}])
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    def test_download_document_disables_redirects(self):
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=200, content_type="application/octet-stream",
                                  content=b"PK\x03\x04")

        with patch.object(client.session, "get", return_value=response) as mock_get:
            content = client.download_document("S100ABCD")

        self.assertEqual(content, b"PK\x03\x04")
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    def test_download_document_rejects_html_response(self):
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=200, content_type="text/html")

        with patch.object(client.session, "get", return_value=response):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.download_document("S100ABCD")

        self.assertNotIn(FAKE_API_KEY, str(ctx.exception))

    def test_http_401_still_raises_through_the_request_exception_path(self):
        # EdinetAPIError is not a RequestException, so the validator does not
        # disturb the pre-existing HTTPError handling: raise_for_status() fires
        # first and the except RequestException clause rewraps it as before.
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=401, content_type="application/json")
        response.reason = "Unauthorized"
        # requests appends " for url: <full url>" to the HTTPError message, and
        # that URL carries the key. Reproduce the real message shape so this
        # test would fail if the caller interpolated the exception directly.
        error = requests.exceptions.HTTPError(
            f"401 Client Error: Unauthorized for url: {response.url}"
        )
        error.response = response
        response.raise_for_status.side_effect = error

        with patch.object(client.session, "get", return_value=response):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.get_documents("2026-08-29")

        self.assertIn("401", str(ctx.exception))
        self.assertNotIn(FAKE_API_KEY, str(ctx.exception))

    def test_download_connection_error_message_omits_the_key(self):
        # ConnectionError messages embed the request URL too, and this one is
        # written to the on-disk log by the caller.
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        error = requests.exceptions.ConnectionError(
            "Max retries exceeded with url: /api/v2/documents/S100ABCD"
            f"?type=1&Subscription-Key={FAKE_API_KEY}"
        )

        with patch.object(client.session, "get", side_effect=error):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.download_document("S100ABCD")

        message = str(ctx.exception)
        self.assertIn("S100ABCD", message)
        self.assertNotIn(FAKE_API_KEY, message)

    def test_non_json_body_under_json_content_type_raises_informative_error(self):
        # requests.exceptions.JSONDecodeError is a RequestException subclass,
        # so without explicit handling it would be rewrapped into exactly the
        # opaque message this change exists to replace.
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=200, content_type="application/json")
        # The real class, so this test also pins the MRO assumption the
        # comment above relies on: JSONDecodeError is both a ValueError
        # (caught by the inner clause) and a RequestException (which would
        # otherwise rewrap it opaquely in the outer clause).
        response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Expecting value", "", 0
        )

        with patch.object(client.session, "get", return_value=response):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.get_documents("2026-08-29")

        message = str(ctx.exception)
        self.assertIn("not valid JSON", message)
        self.assertIn("documents.json", message)
        self.assertNotIn(FAKE_API_KEY, message)

    def test_json_array_body_raises_instead_of_attribute_error(self):
        client = self.fetch.EdinetClient(api_key=FAKE_API_KEY)
        response = _make_response(status_code=200, content_type="application/json",
                                  json_data=[])

        with patch.object(client.session, "get", return_value=response):
            with self.assertRaises(EdinetAPIError) as ctx:
                client.get_documents("2026-08-29")

        self.assertIn("expected a JSON object", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
