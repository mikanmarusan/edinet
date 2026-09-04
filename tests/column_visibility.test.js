// node:test suite for the DOM-free column-visibility state logic in web/script.js.
// Zero new dependencies: requires the real module via its guarded CommonJS shim.
const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
    DEFAULT_HIDDEN_COLUMNS,
    defaultColumnVisible,
    COLUMN_VISIBILITY_SCHEMA_VERSION,
    COLUMN_DEFINITIONS,
    computeInitialState,
    resetVisibilityState
} = require('../script.js');

test('requiring web/script.js does not throw "document is not defined"', () => {
    // Reaching this point means the require above succeeded under node:test (no DOM).
    assert.equal(typeof computeInitialState, 'function');
});

test('all DEFAULT_HIDDEN_COLUMNS keys resolve to defaultColumnVisible === false', () => {
    for (const key of DEFAULT_HIDDEN_COLUMNS) {
        assert.equal(defaultColumnVisible(key), false, `${key} should default hidden`);
    }
});

test('non-listed and required columns resolve to defaultColumnVisible === true', () => {
    assert.equal(defaultColumnVisible('netSales'), true);
    assert.equal(defaultColumnVisible('secCode'), true);
});

test('DEFAULT_HIDDEN_COLUMNS has exactly the 6 expected keys', () => {
    assert.deepEqual(
        [...DEFAULT_HIDDEN_COLUMNS].sort(),
        ['ev', 'evPerEbitda', 'marketCapitalization', 'pbr', 'per', 'stockPrice'].sort()
    );
});

test('legacy bare-map value (no v field) migrates to the new defaults', () => {
    const raw = JSON.stringify({ stockPrice: true, per: true });
    const state = computeInitialState(raw, COLUMN_DEFINITIONS);
    for (const key of DEFAULT_HIDDEN_COLUMNS) {
        assert.equal(state[key], false, `${key} should be hidden after legacy migration`);
    }
});

test('stale-version, null, and invalid-JSON all discard saved state and return 6-hidden defaults', () => {
    const inputs = [
        JSON.stringify({ v: 1, state: { stockPrice: true } }),
        null,
        '{not valid json'
    ];
    for (const raw of inputs) {
        assert.doesNotThrow(() => computeInitialState(raw, COLUMN_DEFINITIONS));
        const state = computeInitialState(raw, COLUMN_DEFINITIONS);
        for (const key of DEFAULT_HIDDEN_COLUMNS) {
            assert.equal(state[key], false, `${key} should be hidden for input ${String(raw)}`);
        }
    }
});

test('valid v2 wrapper preserves user customization but forces required columns true', () => {
    const raw = JSON.stringify({
        v: COLUMN_VISIBILITY_SCHEMA_VERSION,
        state: { per: true, secCode: false }
    });
    const state = computeInitialState(raw, COLUMN_DEFINITIONS);
    assert.equal(state.per, true, 'user customization survives');
    assert.equal(state.secCode, true, 'required column forced visible');
});

test('persistence round-trip: a persisted v2 blob reloads to the same state', () => {
    const defaults = resetVisibilityState(COLUMN_DEFINITIONS);
    const raw = JSON.stringify({ v: COLUMN_VISIBILITY_SCHEMA_VERSION, state: defaults });
    assert.deepEqual(computeInitialState(raw, COLUMN_DEFINITIONS), defaults);
});

test('resetVisibilityState returns the 6-hidden default, not all-visible', () => {
    const state = resetVisibilityState(COLUMN_DEFINITIONS);
    for (const key of DEFAULT_HIDDEN_COLUMNS) {
        assert.equal(state[key], false, `${key} should be hidden on reset`);
    }
    assert.equal(state.netSales, true, 'non-listed column visible on reset');
    assert.equal(state.secCode, true, 'required column visible on reset');
    assert.equal(state.filerName, true, 'required column visible on reset');
});
