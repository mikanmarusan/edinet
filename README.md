# EDINET Financial Data Analysis System

A Python-based tool for retrieving and analyzing financial data from listed companies' securities reports through the EDINET API. This system extracts financial information from XBRL data and compiles it into JSON format for analysis by corporate finance teams and M&A departments.

## Overview

The system consists of two command-line tools:
- **fetch_edinet_financial_documents.py**: Daily data extraction tool that retrieves securities reports for a specific date
- **consolidate_documents.py**: Data consolidation tool that merges multiple daily files into a single consolidated dataset

## Features

- **Automated Data Extraction**: Retrieves securities reports from EDINET API with rate limiting compliance
- **Advanced XBRL Parsing**: Extracts 20+ financial metrics from XBRL documents with dynamic search capabilities
- **Context-Aware Processing**: Prioritizes current year data over historical using XBRL context references
- **Dynamic Search Algorithms**: Sophisticated fallback mechanisms for PER, EPS, and outstanding shares extraction
- **Data Consolidation**: Handles duplicate companies by keeping the latest data
- **Comprehensive Logging**: Detailed logging with configurable verbosity
- **Error Handling**: Robust error handling with retry mechanisms
- **JSON Output**: Clean, structured JSON output with CORS support

## Prerequisites

- Python 3.7+
- EDINET API key (register at https://disclosure2.edinet-fsa.go.jp/)
- Internet connection for API access

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd edinet
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### EDINET API Key

You need to register for an EDINET API key:
1. Visit https://disclosure2.edinet-fsa.go.jp/
2. Register for API access
3. Obtain your API key

## Usage

### Daily Data Extraction

Extract financial data for a specific date:

```bash
# Basic usage
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY

# With verbose logging
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY --verbose

# With custom retry settings
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY --max-retries 5
```

**Required Parameters:**
- `--date`: Date in YYYY-MM-DD format
- `--outputdir`: Output directory for JSON files
- `--api-key`: EDINET API key

**Optional Parameters:**
- `--verbose, -v`: Enable verbose logging
- `--max-retries`: Maximum number of retries for failed requests (default: 3)

**Output:**
- Creates `{outputdir}/{YYYY-MM-DD}.json` with extracted financial data
- Generates log file `fetch_edinet_financial_documents_{YYYYMMDD}.log`

### Data Consolidation

Consolidate multiple daily JSON files:

```bash
# Basic usage
python consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json

# With summary report
python consolidate_documents.py --inputdir data/jsons/ --output data/consolidated.json --summary --verbose
```

**Required Parameters:**
- `--inputdir`: Input directory containing JSON files
- `--output`: Output file path

**Optional Parameters:**
- `--summary`: Display summary report
- `--verbose, -v`: Enable verbose logging

**Output:**
- Creates consolidated JSON file at specified location
- Generates log file `consolidate_documents_{YYYYMMDD}.log`

## Extracted Financial Metrics

The system extracts the following financial metrics from XBRL data:

| Field | Description | Type |
|-------|-------------|------|
| secCode | 4-digit securities code | String |
| periodEnd | Fiscal period end | String |
| characteristic | Company characteristics | String |
| stockPrice | Stock price at fiscal year end | Number |
| netSales | Total net sales | Number |
| employees | Number of employees | Number |
| operatingIncome | Operating income | Number |
| operatingIncomeRate | Operating income rate (%) | Number |
| depreciation | Depreciation expenses | Number |
| ebitda | EBITDA | Number |
| ebitdaMargin | EBITDA margin (%) | Number |
| marketCapitalization | Market capitalization | Number |
| per | Price-to-earnings ratio | Number |
| ev | Enterprise value | Number |
| evPerEbitda | Enterprise value / EBITDA | Number |
| pbr | Price-to-book ratio | Number |
| equity | Total equity/shareholders' equity | Number |
| debt | Net interest-bearing debt | Number |
| outstandingShares | Number of outstanding shares | Number |
| netIncome | Net income attributable to shareholders | Number |
| eps | Earnings per share (diluted preferred) | Number |
| retrievedDate | Data retrieval date | String |

## File Structure

```
project/
├── fetch_edinet_financial_documents.py    # Daily data extraction tool
├── consolidate_documents.py               # Data consolidation tool
├── lib/                                   # Shared utilities module
│   ├── __init__.py                       # Module initialization
│   ├── edinet_common.py                  # Common utilities and configurations
│   └── xbrl_parser.py                    # XBRL parsing functionality
├── requirements.txt                       # Python dependencies
├── README.md                             # This file
├── LICENSE                               # License file
├── CLAUDE.md                            # Project instructions
├── .ai-rules/                            # AI development rules
│   └── edinet_requirements_spec.md       # Product requirements specification
└── data/
    ├── jsons/                           # Daily JSON files
    │   ├── 2025-06-10.json
    │   ├── 2025-06-11.json
    │   └── ...
    └── edinet.json                      # Consolidated output
```

## Development Architecture

### Modular Structure
The system uses a modular architecture with shared utilities:

- **lib/edinet_common.py**: Core utilities including API configuration, XBRL namespaces, logging setup, and data validation functions
- **lib/xbrl_parser.py**: Specialized XBRL document extraction and financial metrics parsing
- **Main scripts**: Import from lib module for shared functionality

### Key Shared Components
- EDINET API configuration and rate limiting
- XBRL namespace mappings for EDINET 2024-11-01 taxonomy  
- Common logging and error handling
- Data validation and formatting utilities

### Advanced XBRL Processing

The system implements sophisticated data extraction algorithms for robust financial metrics capture:

#### Dynamic Search Capabilities
- **PER Extraction**: When standard XBRL patterns fail, dynamically searches for PER-related tags using keyword matching and priority scoring
- **EPS Extraction**: Advanced detection of diluted/basic EPS with context-aware fallback mechanisms and comprehensive tag pattern matching
- **Outstanding Shares**: Sophisticated share count detection with dynamic search across multiple tag variations and context prioritization

#### Context-Aware Processing
- **Current Year Priority**: Automatically prioritizes current fiscal year data over historical data using XBRL context references
- **Priority Scoring**: Implements intelligent scoring algorithms to select the most relevant data when multiple candidates exist
- **Range Validation**: Filters unreasonable values (e.g., PER > 1000, shares outside typical ranges) to ensure data quality

## API Rate Limiting

The system automatically enforces EDINET API rate limits:
- Maximum 1 request per second
- Automatic retry with exponential backoff for failed requests
- Comprehensive error handling for network issues

## Error Handling

The system includes robust error handling for:
- **Missing Data**: Skips companies with incomplete data
- **API Errors**: Logs errors and continues processing
- **File I/O Errors**: Displays clear error messages
- **Network Issues**: Implements retry logic with delays
- **XBRL Parsing Errors**: Handles malformed or incomplete XBRL data

## Logging

Both tools generate detailed logs:
- Console output for real-time monitoring
- Log files for detailed debugging
- Configurable verbosity levels
- Progress indicators for long-running operations

## Data Quality

The system ensures data quality through:
- **Data Validation**: Validates extracted financial metrics
- **Missing Fields**: Handles incomplete XBRL data gracefully
- **Data Consistency**: Ensures consistent data types across output
- **Duplicate Handling**: Latest data takes precedence in consolidation

## Workflow Example

1. **Daily Extraction**:
```bash
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY
```

2. **Repeat for Multiple Days**:
```bash
python fetch_edinet_financial_documents.py --date 2025-06-11 --outputdir data/jsons --api-key YOUR_API_KEY
python fetch_edinet_financial_documents.py --date 2025-06-12 --outputdir data/jsons --api-key YOUR_API_KEY
```

3. **Consolidate Data**:
```bash
python consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json --summary
```

4. **Result**: Consolidated financial data in `data/edinet.json`

## Troubleshooting

### Common Issues

1. **API Key Issues**:
   - Ensure your API key is valid and active
   - Check EDINET API service status

2. **No Data Found**:
   - Verify the date format (YYYY-MM-DD)
   - Check if securities reports were filed on that date

3. **Network Errors**:
   - Check internet connectivity
   - API might be temporarily unavailable

4. **XBRL Parsing Errors**:
   - Some companies may have non-standard XBRL formats
   - The system will skip and log these errors

### Log Files

Check log files for detailed error information:
- `fetch_edinet_financial_documents_{YYYYMMDD}.log`: Daily extraction logs
- `consolidate_documents_{YYYYMMDD}.log`: Consolidation logs

## Development

### Running Tests

When you have an API key available, test the tools:

```bash
# Test fetch_edinet_financial_documents with a recent date
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY --verbose

# Test consolidate_documents with generated data
python consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json --summary --verbose
```

### Contributing

1. Follow the existing code style
2. Add appropriate error handling
3. Update documentation for new features
4. Test with real EDINET data

## License

See LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review log files for error details
- Ensure API key is valid and active
