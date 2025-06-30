# EDINET Tests

This directory contains test cases for EDINET tools functionality.

## Running Tests

### Using pytest (recommended)
```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_stock_exchange_mapping.py -v
```

### Using unittest
```bash
# Run specific test file
python tests/test_stock_exchange_mapping.py

# Run with verbose output
python tests/test_stock_exchange_mapping.py -v
```

## Test Coverage

### test_stock_exchange_mapping.py
Tests for the stock exchange mapping functionality:
- **Nagoya Stock Exchange (N)**: Tests all security codes mapped to Nagoya
- **Fukuoka Stock Exchange (F)**: Tests all security codes mapped to Fukuoka
- **Sapporo Stock Exchange (S)**: Tests all security codes mapped to Sapporo
- **Tokyo Stock Exchange (T)**: Tests default mapping for unmapped codes
- **Cache functionality**: Ensures mapping is cached after first load
- **Error handling**: Tests behavior when config file is missing or invalid
- **Edge cases**: Tests empty strings, invalid codes, etc.
- **Yahoo URL generation**: Tests correct URL format with exchange codes

## Dependencies
- Python 3.x
- unittest (built-in)
- pytest (optional, for enhanced test runner)
- PyYAML (required by edinet_common module)