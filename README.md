# EDINET Financial Data Analysis System

A Python-based tool for retrieving and analyzing financial data from listed companies' securities reports through the EDINET API.

## Overview

This system provides comprehensive financial data extraction and analysis capabilities for Japanese listed companies through the EDINET (Electronic Disclosure for Investors' NETwork) system. It automatically retrieves securities reports (有価証券報告書) submitted to Japan's Financial Services Agency and transforms complex XBRL financial data into structured, analysis-ready JSON format.

**Who Uses This Tool:**
- Corporate Finance Teams - For competitor analysis and market research
- M&A Departments - For due diligence and valuation analysis
- Investment Analysts - For financial modeling and screening
- Data Scientists - For building financial datasets and models

**Key Features:**
- **Automated Data Collection**: Daily extraction from EDINET API with intelligent retry mechanisms
- **Comprehensive Metrics**: Extraction of 25+ key financial indicators including P&L, balance sheet, and market data
- **Yahoo Finance Integration**: Enriched data with real-time stock prices and market metrics
- **Flexible Filtering**: Target specific companies using security codes
- **Data Consolidation**: Merge multiple daily extracts into unified datasets
- **Enterprise Value Calculations**: Automated EV, EBITDA, and EV/EBITDA calculations
- **Clean JSON Output**: Structured format optimized for analysis and integration

## Prerequisites

- Python 3.7+
- EDINET API key (register at https://disclosure2.edinet-fsa.go.jp/)
- Internet connection

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

## Quick Start

### 1. Get Your API Key

Register at https://disclosure2.edinet-fsa.go.jp/ to obtain an EDINET API key.

### 2. Extract Daily Data

```bash
python bin/fetch_edinet_financial_documents.py \
  --date 2025-06-10 \
  --outputdir data/jsons \
  --api-key YOUR_API_KEY
```

### 3. Consolidate Multiple Days

```bash
python bin/consolidate_documents.py \
  --inputdir data/jsons/ \
  --output data/edinet.json \
  --summary
```

## Command Reference

### fetch_edinet_financial_documents.py

Extracts financial data for a specific date.

**Required Parameters:**
- `--date`: Date in YYYY-MM-DD format
- `--outputdir`: Output directory for JSON files
- `--api-key`: Your EDINET API key

**Optional Parameters:**
- `--verbose, -v`: Enable detailed logging
- `--max-retries`: Maximum retry attempts (default: 3)
- `--sec-codes`: Comma-separated list of security codes to filter (e.g., 7203,9984)

**Output:** Creates `{outputdir}/{YYYY-MM-DD}.json`

### consolidate_documents.py

Consolidates multiple daily JSON files into a single file.

**Required Parameters:**
- `--inputdir`: Directory containing daily JSON files
- `--output`: Output file path

**Optional Parameters:**
- `--summary`: Display summary statistics
- `--verbose, -v`: Enable detailed logging

**Output:** Creates consolidated JSON file

## Extracted Financial Metrics

| Field | Description | Type |
|-------|-------------|------|
| docID | EDINET document ID | String |
| secCode | 4-digit securities code | String |
| filerName | Company name | String |
| docPdfURL | Securities report PDF URL | String |
| yahooURL | Yahoo Finance URL | String |
| periodEnd | Fiscal period end (YYYY年M月期) | String |
| characteristic | Company characteristics | String |
| stockPrice | Stock price at fiscal year end | Number |
| netSales | Total net sales | Number |
| employees | Number of employees | Number |
| operatingIncome | Operating income | Number |
| operatingIncomeRate | Operating income rate (%) | Number |
| ordinaryIncome | Ordinary income | Number |
| ordinaryIncomeRate | Ordinary income rate (%) | Number |
| depreciation | Depreciation | Number |
| marketCapitalization | Market capitalization | Number |
| per | Price-to-earnings ratio | Number |
| pbr | Price-to-book ratio | Number |
| bps | Book value per share | Number |
| equity | Total equity | Number |
| debt | Net interest-bearing debt | Number |
| outstandingShares | Outstanding shares | Number |
| netIncome | Net income | Number |
| eps | Earnings per share | Number |
| cash | Cash and cash equivalents | Number |
| issuedDate | Securities report submission date | String |
| ebitda | EBITDA | Number |
| ebitdaMargin | EBITDA margin (%) | Number |
| ev | Enterprise value | Number |
| evPerEbitda | EV/EBITDA ratio | Number |
| retrievedDate | Data retrieval date | String |

## Example Workflow

```bash
# Day 1: Extract data
python bin/fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_KEY

# Day 2: Extract data
python bin/fetch_edinet_financial_documents.py --date 2025-06-11 --outputdir data/jsons --api-key YOUR_KEY

# Day 3: Extract data
python bin/fetch_edinet_financial_documents.py --date 2025-06-12 --outputdir data/jsons --api-key YOUR_KEY

# Consolidate all data
python bin/consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json --summary
```

## Troubleshooting

### Common Issues

**No Data Found**
- Verify the date format (YYYY-MM-DD)
- Securities reports may not be filed on weekends/holidays
- Check if the date is too recent (data may not be available yet)

**API Key Issues**
- Ensure your API key is valid and active
- Check EDINET API service status

**Network Errors**
- Verify internet connectivity
- The tool will automatically retry failed requests

**XBRL Parsing Errors**
- Some companies may have non-standard formats
- The system will skip problematic files and continue

### Log Files

Check logs for detailed information:
- `fetch_edinet_financial_documents_{YYYYMMDD}.log`
- `consolidate_documents_{YYYYMMDD}.log`

## Output Format

The system generates JSON files with the following structure:

```json
{
  "companies": [
    {
      "secCode": "1234",
      "periodEnd": "2025年3月期",
      "netSales": 1000000000,
      "employees": 500,
      // ... other metrics
    }
  ]
}
```

## Technical Documentation

For developers and technical details, see:
- `.claude/` - Development guidelines
- `CLAUDE.md` - AI assistant instructions

## License

See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review log files for detailed error messages
3. Ensure your API key is valid
4. Open an issue on GitHub if problems persist