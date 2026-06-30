# XBRL test fixtures (synthetic)

These XBRL instance documents are **synthetic**. Every figure is an
obviously-fake round number for a fictitious filer (entity `E00001`,
securities code `9999`) - never a real company's reported value. They are
round-trip anchors: a value placed in the fixture is asserted to come back out,
validating extraction wiring, not any real filing's numbers.

| Fixture | Taxonomy edition | Standard | Purpose |
| --- | --- | --- | --- |
| `consolidated_jgaap_2024.xbrl` | 2024-11-01 | JGAAP | Baseline consolidated filer; exercises every tracked field |
| `consolidated_jgaap_2025.xbrl` | 2025-11-01 | JGAAP | Same facts on the newer edition; proves cross-edition determinism |
| `ifrs_2024.xbrl` | 2024-11-01 | IFRS | jpigp `EquityIFRS` + jpcrp IFRS revenue; `ordinaryIncome` must be null |
| `bank_2024.xbrl` | 2024-11-01 | JGAAP | Bank/insurer structure (経常収益/経常利益); must extract without crashing |
| `consolidated_vs_parent_2024.xbrl` | 2024-11-01 | JGAAP | Consolidated and parent-only contexts differ; consolidated must win |
| `tie_break_2024.xbrl` | 2024-11-01 | JGAAP | Two equal-priority sales tags; pins the deterministic tag-name tiebreak |

## Consumers

- `tests/_xbrl_fixture_utils.py` - shared loader (`parse_fixture`) and the
  tracked-field list.
- `tests/test_golden_regression.py` - golden-master harness; gates on zero
  unexplained `REGRESSION` rows against `tests/golden/golden_baseline.json`.
- `tests/test_ifrs_extraction.py` - IFRS criteria (jpigp resolves, ordinary
  income null, equity/net_sales/net_income extract).
- `tests/test_fixture_extraction.py` - cross-edition determinism,
  consolidated-over-parent, bank no-crash, docURL.

## Re-baselining the golden file

When a deliberate extraction change shifts a value, add an `EXPECTED_CHANGES`
entry in `test_golden_regression.py` (so the row reads `fix`, not
`REGRESSION`). Once accepted, regenerate the baseline and drop the entry:

```bash
REGEN_GOLDEN=1 python -m pytest tests/test_golden_regression.py
```

The baseline is generated, never hand-edited.
