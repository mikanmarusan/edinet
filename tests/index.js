// Directory entry point for the node:test runner.
//
// `node --test web/tests/` resolves the directory via CommonJS module resolution
// (Node's positional --test arg does not recursively discover files), so this
// index requires each test file to register its tests. Add new *.test.js files
// here to keep the `node --test web/tests/` acceptance command green.
require('./column_visibility.test.js');
