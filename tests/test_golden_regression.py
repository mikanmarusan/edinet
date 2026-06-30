"""Golden regression harness for XBRL field extraction (issue #187, PR6).

The harness re-extracts every fixture under ``tests/fixtures/xbrl/`` and diffs
each tracked field against a committed golden baseline. Each comparison yields a
row ``field | old | new | golden | delta% | verdict`` where the verdict is one
of:

* ``match``      - new value equals the golden baseline (no change).
* ``fix``        - new value differs but the change is intentional and listed in
                   ``EXPECTED_CHANGES`` (a deliberate extraction improvement).
* ``REGRESSION`` - new value differs and is NOT allowlisted; the test fails.

The suite gates CI on **zero unexplained REGRESSION rows**. When a deliberate
extraction change lands, add an ``EXPECTED_CHANGES`` entry (so the row reads
``fix``); once the change is accepted, re-baseline with
``REGEN_GOLDEN=1 python -m pytest tests/test_golden_regression.py`` and drop the
allowlist entry. The baseline is regenerated, never hand-edited.

All fixture values are synthetic - see ``tests/fixtures/xbrl/README.md``.
"""
import json
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from _xbrl_fixture_utils import FIXTURES, GOLDEN_FIELDS, parse_fixture

GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'golden', 'golden_baseline.json')

# Allowlist of intentional extraction changes, keyed by (fixture, field) -> new
# value. An entry here turns an otherwise-REGRESSION row into a ``fix`` row so
# the gate passes. Empty in steady state: the committed baseline already matches
# current extraction.
EXPECTED_CHANGES = {
    # ('consolidated_jgaap_2024.xbrl', 'debt'): -1500000000.0,
}

# Relative tolerance for float comparison (extraction is exact, but floats from
# division - per/pbr - can carry representation noise).
REL_TOL = 1e-9


def _load_golden():
    with open(GOLDEN_PATH, encoding='utf-8') as f:
        return json.load(f)


def _values_equal(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        denom = max(abs(a), abs(b), 1.0)
        return abs(a - b) / denom <= REL_TOL
    return a == b


def _delta_pct(old, new):
    if isinstance(old, (int, float)) and isinstance(new, (int, float)) and old:
        return f'{(new - old) / abs(old) * 100:+.1f}%'
    return '-'


def _verdict(fixture, field, old, new):
    if _values_equal(old, new):
        return 'match'
    if (fixture, field) in EXPECTED_CHANGES and _values_equal(EXPECTED_CHANGES[(fixture, field)], new):
        return 'fix'
    return 'REGRESSION'


def _regenerate_baseline():
    baseline = {}
    for name in FIXTURES:
        res = parse_fixture(name)
        baseline[name] = {f: res.get(f) for f in GOLDEN_FIELDS}
    with open(GOLDEN_PATH, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


class TestGoldenRegression(unittest.TestCase):
    """Diff current extraction against the committed golden baseline."""

    @classmethod
    def setUpClass(cls):
        if os.environ.get('REGEN_GOLDEN') == '1':
            _regenerate_baseline()
        cls.golden = _load_golden()

    def test_no_unexplained_regressions(self):
        rows = []
        regressions = []
        for fixture in FIXTURES:
            self.assertIn(fixture, self.golden,
                          f'{fixture} missing from golden baseline; run REGEN_GOLDEN=1')
            extracted = parse_fixture(fixture)
            golden_fields = self.golden[fixture]
            for field in GOLDEN_FIELDS:
                old = golden_fields.get(field)
                golden = old  # baseline is the authoritative golden value
                new = extracted.get(field)
                verdict = _verdict(fixture, field, golden, new)
                rows.append((fixture, field, old, new, golden, _delta_pct(old, new), verdict))
                if verdict == 'REGRESSION':
                    regressions.append((fixture, field, old, new))

        # Emit the harness table so it is visible on failure / with -s.
        header = f'{"fixture":34} {"field":18} {"old":>16} {"new":>16} {"delta%":>8} {"verdict"}'
        lines = [header, '-' * len(header)]
        for fixture, field, old, new, golden, delta, verdict in rows:
            lines.append(f'{fixture:34} {field:18} {str(old):>16} {str(new):>16} {delta:>8} {verdict}')
        table = '\n'.join(lines)

        self.assertEqual(
            regressions, [],
            msg='Unexplained REGRESSION rows (add an EXPECTED_CHANGES entry if '
                f'intentional, else fix the extractor):\n{table}',
        )

    def test_golden_covers_all_tracked_fields(self):
        """Every fixture's golden record carries every tracked field, so a
        newly-tracked field cannot silently skip the regression gate."""
        for fixture in FIXTURES:
            for field in GOLDEN_FIELDS:
                self.assertIn(field, self.golden[fixture],
                              f'{fixture} golden record is missing tracked field {field}')


if __name__ == '__main__':
    unittest.main()
