# EDINET Financial Data Analysis Software Requirements Specification

## 1. Project Overview

### 1.1 Purpose
This software system is designed to retrieve and analyze financial data from listed companies' securities reports through the EDINET API. It consists of two command-line tools that extract financial information from XBRL data and compile it into JSON format for analysis by corporate finance teams and M&A departments.

### 1.2 Target Users
- Corporate finance personnel
- M&A team members
- Financial analysts investigating listed company information

### 1.3 System Architecture
The system consists of two Python-based command-line tools:
1. **fetch_edinet_financial_documents.py**: Daily data extraction tool
2. **consolidate_documents.py**: Data consolidation tool

## 2. Functional Requirements

### 2.1 fetch_edinet_financial_documents.py: Daily Data Extraction Tool

#### 2.1.1 Basic Functionality
- Retrieve securities reports submitted on a specific date via EDINET API
- Parse XBRL data from securities reports
- Extract predefined financial metrics
- Output data in JSON format

#### 2.1.2 Command Line Interface
```bash
python fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY
```

#### 2.1.2.1 Required Parameters
- `--date`: Date in YYYY-MM-DD format
- `--outputdir`: Output directory for JSON files  
- `--api-key`: EDINET API key

#### 2.1.2.2 Optional Parameters
- `--verbose, -v`: Enable verbose logging
- `--max-retries`: Maximum number of retries for failed requests (default: 3)
- `--sec-codes`: Comma-separated list of security codes to filter (e.g., 7203,9984,4755)

#### 2.1.3 Data Extraction Requirements
Extract the following financial data from XBRL:

| Field Name | Description | Example |
|------------|-------------|---------|
| secCode | 4-digit securities code | 4384 |
| periodEnd | Fiscal period end | "2024年7月期" |
| characteristic | Company characteristics | Business description |
| stockPrice | Stock price at fiscal year end or current | 1250 |
| netSales | Total net sales at period end | 15000000000 |
| employees | Number of employees at period end | 500 |
| operatingIncome | Operating income | 1200000000 |
| operatingIncomeRate | Operating income rate | 8.0 |
| depreciation | Depreciation expenses | 300000000 |
| ebitda | EBITDA | 1500000000 |
| ebitdaMargin | EBITDA margin | 10.0 |
| marketCapitalization | Market capitalization | 50000000000 |
| per | Price-to-earnings ratio | 25.5 |
| ev | Enterprise value (Market cap + Net debt) | 52000000000 |
| evPerEbitda | Enterprise value / EBITDA | 34.7 |
| pbr | Price-to-book ratio | 3.2 |
| bps | Book value per share | 375.0 |
| equity | Total equity/shareholders' equity | 15000000000 |
| debt | Net interest-bearing debt (excluding cash) | 2000000000 |
| outstandingShares | Number of outstanding shares | 40000000 |
| netIncome | Net income attributable to shareholders | 800000000 |
| eps | Earnings per share (diluted preferred) | 20.0 |
| cash | Cash and cash equivalents at end of period | 5000000000 |
| retrievedDate | Data retrieval date | "2025-06-10" |
| docPdfURL | Direct URL to EDINET PDF document | "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/{docID}.pdf" |
| yahooURL | Yahoo Finance URL with stock exchange suffix | "https://finance.yahoo.co.jp/quote/{secCode}.{exchangeCode}" |

#### 2.1.3.1 Security Code Filtering
When `--sec-codes` option is specified:
- Only process companies whose security codes match the provided list
- Skip all other companies before XBRL download to minimize API calls
- Accept comma-separated list of 4 or 5-digit security codes
- Normalize codes to 4-digit format (remove trailing zero from 5-digit codes)
- Log skipped companies at debug level

#### 2.1.4 Output Specification
- **File Format**: JSON
- **File Location**: `{outputdir}/{YYYY-MM-DD}.json`
- **Data Structure**: Array of company objects
- **Log Files**: `fetch_edinet_financial_documents_{YYYYMMDD}.log`
- **CORS Support**: Enable CORS for web access

#### 2.1.4.1 Period End Format
- Convert from YYYY-MM-DD to YYYY年MM月期 format
- Single-digit months without leading zeros (e.g., "2025年3月期")

#### 2.1.4.2 Securities Code Format  
- 4-digit securities code format
- Remove trailing zero if 5-digit code provided

#### 2.1.5 JSON Output Format
```json
[
  {
    "secCode": "4384",
    "filerName": "ラクスル株式会社",
    "docID": "S100TZ9X",
    "docPdfURL": "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100TZ9X.pdf",
    "yahooURL": "https://finance.yahoo.co.jp/quote/4384.T",
    "periodEnd": "2024年7月期",
    "retrievedDate": "2025-06-10",
    "characteristic": "印刷・物流プラットフォーム事業を展開",
    "stockPrice": 1250,
    "netSales": 15000000000,
    "employees": 500,
    "operatingIncome": 1200000000,
    "operatingIncomeRate": 8.0,
    "depreciation": 300000000,
    "ebitda": 1500000000,
    "ebitdaMargin": 10.0,
    "marketCapitalization": 50000000000,
    "per": 25.5,
    "ev": 52000000000,
    "evPerEbitda": 34.7,
    "pbr": 3.2,
    "bps": 375.0,
    "equity": 15000000000,
    "debt": 2000000000,
    "outstandingShares": 40000000,
    "netIncome": 800000000,
    "eps": 20.0,
    "cash": 5000000000
  }
]
```

### 2.2 consolidate_documents.py: Data Consolidation Tool

#### 2.2.1 Basic Functionality
- Read multiple JSON files generated by fetch_edinet_financial_documents.py
- Consolidate data from the past year
- Handle duplicate companies by keeping the latest data
- Output consolidated data in JSON format

#### 2.2.2 Command Line Interface
```bash
python consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json
```

#### 2.2.2.1 Required Parameters
- `--inputdir`: Input directory containing JSON files
- `--output`: Output file path

#### 2.2.2.2 Optional Parameters
- `--summary`: Display summary report
- `--verbose, -v`: Enable verbose logging

#### 2.2.3 Data Processing Rules
- **Duplicate Handling**: For companies appearing in multiple files, retain only the data from the latest `retrievedDate`
- **Data Scope**: Process all JSON files in the specified input directory
- **Output Format**: Same JSON structure as Tool 1

#### 2.2.4 Output Specification
- **File Format**: JSON
- **File Location**: User-specified output path (required parameter)
- **Log Files**: `consolidate_documents_{YYYYMMDD}.log`
- **CORS Support**: Enable CORS for web access

## 3. Technical Requirements

### 3.1 Development Environment
- **Programming Language**: Python
- **Target Platform**: Command-line interface
- **External Dependencies**: EDINET API, XBRL parsing libraries

### 3.2 API Integration
- **API Endpoint**: EDINET API
- **API Documentation**: https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html
- **Rate Limiting**: Maximum 1 request per second
- **Authentication**: API key required (must be obtained from EDINET registration)

### 3.3 Data Sources
- **Primary Source**: EDINET API securities reports
- **Data Format**: XBRL format
- **Stock Price Source**: Extract from securities reports' XBRL data
- **Target Scope**: All listed companies

### 3.4 XBRL Processing
- Parse XBRL taxonomy according to EDINET specifications
- Extract financial data using standard XBRL tags
- Refer to EDINET API documentation for tag mapping

#### 3.4.1 Taxonomy Version
- Target taxonomy: EDINET 2024-11-01
- Supported namespaces:
  - jpcrp_cor: http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-11-01/jpcrp_cor
  - jppfs_cor: http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-11-01/jppfs_cor
  - jpigp_cor: http://disclosure.edinet-fsa.go.jp/taxonomy/jpigp/2024-11-01/jpigp_cor

#### 3.4.2 Advanced XBRL Processing Features
The system implements sophisticated data extraction algorithms:

**Dynamic Search Algorithms:**
- **PER Extraction**: When standard XBRL patterns fail, dynamically searches for PER-related tags with priority scoring
- **EPS Extraction**: Advanced detection of diluted/basic EPS with context-aware fallback mechanisms
- **Outstanding Shares**: Comprehensive share count detection with dynamic tag search capabilities
- **Cash Extraction**: Period-end prioritized extraction of cash and cash equivalents with consolidated data preference

**Context-Aware Processing:**
- **Current Year Priority**: Prioritizes current fiscal year data over historical data using XBRL context references
- **Consolidated Data Priority**: Systematically excludes NonConsolidatedMember contexts to ensure consolidated financial data
- **Priority Scoring**: Implements scoring algorithms to select the most relevant data when multiple candidates exist
- **Fallback Mechanisms**: Multiple extraction strategies ensure robust data capture even with non-standard XBRL formats
- **Context Hierarchy**: Established priority order: Consolidated+CurrentYear > CurrentYear > Consolidated > Others

**Data Quality Enhancement:**
- **Range Validation**: Filters unreasonable values (e.g., PER > 1000, shares outside typical ranges)
- **Context Prioritization**: Uses XBRL context references to identify and prefer current year data
- **Tag Keyword Matching**: Advanced pattern matching for tags when standard taxonomy patterns don't match

#### 3.4.3 Outstanding Shares (発行済株式総数) Extraction Specification

**Definition:**
- **Outstanding Shares (発行済株式総数)**: Total number of shares issued by the company, including treasury stock
- **Float (流通株式数)**: Outstanding shares minus treasury stock

**XBRL Tag Priority Order:**

1. **Highest Priority: Summary of Business Results Tags**
   - `TotalNumberOfIssuedSharesSummaryOfBusinessResults`
   - Most authoritative source from the summary section of securities reports

2. **High Priority: General Total Issued Shares Tags**
   - `TotalNumberOfIssuedShares`
   - `TotalNumberOfSharesIssued`
   - `NumberOfSharesIssuedAtTheEndOfFiscalYear`
   - `NumberOfIssuedSharesAtTheEndOfFiscalYear`

3. **Medium Priority: Standard Issued Shares Tags**
   - `NumberOfIssuedShares`
   - `SharesIssued`
   - `IssuedShares`

4. **Common Stock Specific Tags**
   - `NumberOfSharesIssuedCommonStock`
   - `CommonStockNumberOfSharesIssued`
   - `CommonStockSharesIssued`
   - `CapitalStockNumberOfShares`

5. **Lower Priority: Outstanding Shares Tags**
   - `NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYear`
   - `NumberOfIssuedAndOutstandingShares`
   - `NumberOfSharesOutstanding`
   - `SharesOutstanding`
   - Note: These may represent shares excluding treasury stock

6. **Lowest Priority: Tags Explicitly Including Treasury Stock**
   - `NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock`
   - `NumberOfSharesOutstandingIncludingTreasuryStock`

**Dynamic Search Priority Scoring:**

*Positive Scoring:*
- `totalnumberofsharesissued`: +25 points
- `numberofissuedandoutstandingshares` (without treasury): +23 points
- `sharesissued` (without treasury): +20 points
- `outstanding` (without treasury): +15 points
- `issued` (without treasury): +12 points
- End of period indicators (`attheendof`, `endof`, `fiscal`, `year`): +10 points
- Common stock indicators (`common`): +8 points

*Negative Scoring:*
- `treasury` (treasury stock indicator): -20 points
- `authorized` (authorized shares): -10 points

**Implementation Notes:**
- Context filtering: Exclude `NonConsolidatedMember` contexts
- Valid range: 1,000 to 100,000,000,000 shares
- Priority: CurrentYear contexts over historical data
- Fallback: Dynamic search when standard patterns fail

#### 3.4.4 Stock Exchange Code Determination

**Purpose:**
Generate appropriate Yahoo Finance URLs by determining the stock exchange where each security is listed.

**Implementation:**
- **Configuration File**: `config/stock_exchange_mapping.yml` contains security code to exchange mappings
- **Function**: `get_stock_exchange_code(sec_code)` in `lib/edinet_common.py`
- **Caching**: Mapping is loaded once and cached to avoid repeated file I/O

**Exchange Codes:**
- **T**: Tokyo Stock Exchange (東京証券取引所) - Default
- **N**: Nagoya Stock Exchange (名古屋証券取引所)
- **F**: Fukuoka Stock Exchange (福岡証券取引所)
- **S**: Sapporo Stock Exchange (札幌証券取引所)

**Yahoo Finance URL Format:**
```
https://finance.yahoo.co.jp/quote/{secCode}.{exchangeCode}
```

**Processing Logic:**
1. Load stock exchange mapping from YAML configuration file
2. Look up security code in the mapping
3. Return mapped exchange code if found
4. Return 'T' (Tokyo) as default for unmapped codes
5. Handle errors gracefully (missing file, invalid YAML) by defaulting to Tokyo

**Configuration File Format:**
```yaml
stock_exchanges:
  "1738": "N"  # Nagoya
  "1771": "F"  # Fukuoka
  "1449": "S"  # Sapporo
  # ... additional mappings
```

**Error Handling:**
- Missing configuration file: Log warning and default all codes to Tokyo
- Invalid YAML format: Log warning and default all codes to Tokyo
- Empty mapping: Default all codes to Tokyo

## 4. Non-Functional Requirements

### 4.1 Performance Requirements
- **API Rate Limit Compliance**: Enforce 1-second interval between API requests
- **Processing Scope**: Handle all listed companies (approximately 3,000+ companies)
- **Data Freshness**: Process the latest available securities reports for each company

### 4.2 Error Handling
- **Missing Data**: Skip companies with incomplete data and continue processing
- **API Errors**: Log errors to console and continue with next company
- **File I/O Errors**: Display error messages to console
- **Network Issues**: Implement retry logic with appropriate delays

### 4.3 Logging and Monitoring
- **Log Output**: Console output + file logging
- **Verbosity Control**: Configurable via `--verbose` option
- **Log File Naming**: `{script_name}_{YYYYMMDD}.log`
- **Error Messages**: Display clear error descriptions
- **Progress Indicators**: Show processing progress where applicable

### 4.4 Data Quality
- **Data Validation**: Validate extracted financial metrics for reasonability
- **Missing Fields**: Handle cases where XBRL data is incomplete
- **Data Consistency**: Ensure consistent data types across output files

## 5. System Integration

### 5.1 File System Organization
```
project/
├── fetch_edinet_financial_documents.py
├── consolidate_documents.py
├── lib/
│   ├── __init__.py
│   ├── edinet_common.py
│   └── xbrl_parser.py
├── .ai-rules/
│   └── edinet_requirements_spec.md
└── data/
    ├── jsons/
    │   ├── 2025-06-10.json
    │   ├── 2025-06-11.json
    │   └── ...
    └── edinet.json
```

### 5.2 Workflow
1. Execute fetch_edinet_financial_documents.py with specific date parameter
2. fetch_edinet_financial_documents.py retrieves securities reports from EDINET API
3. Parse XBRL data and extract financial metrics
4. Save daily results to `{outputdir}/{date}.json`
5. Execute consolidate_documents.py to consolidate historical data
6. consolidate_documents.py processes all files in specified input directory
7. Generate consolidated output at specified output path

### 5.3 Data Flow
```
EDINET API → XBRL Data → fetch_edinet_financial_documents.py → Daily JSON Files → consolidate_documents.py → Consolidated JSON
```

## 6. Constraints and Assumptions

### 6.1 External Dependencies
- EDINET API availability and stability
- XBRL data format consistency across different companies
- Network connectivity for API access

#### 6.1.1 EDINET Data Scope
**Available from XBRL:**
- secCode, filerName, docID, periodEnd
- netSales, employees, operatingIncome, equity, netIncome, cash
- outstandingShares, eps (basic/diluted with dynamic extraction)
- per (with dynamic search capabilities when standard patterns fail)
- stockPrice, depreciation, marketCapitalization, pbr, debt, characteristic (when available)
- Calculated metrics: operatingIncomeRate, ebitda, ebitdaMargin, ev, evPerEbitda

**Variable Availability:**
- Some fields may not be available for all companies due to XBRL reporting variations
- Dynamic search algorithms improve data extraction success rates
- Missing fields are set to null in JSON output

### 6.2 Data Limitations
- Financial data availability depends on companies' reporting schedules
- XBRL tag variations between different companies
- Historical data limited to available securities reports

### 6.3 Technical Constraints
- Python environment required for execution
- File system access for data storage
- Internet connectivity for API access

## 7. Future Considerations

### 7.1 Scalability
- Consider database storage for large datasets
- Implement parallel processing for faster data extraction
- Add data caching mechanisms

### 7.2 Enhancement Opportunities
- Web-based user interface
- Real-time data updates
- Advanced financial analysis features
- Data visualization capabilities

## 8. Acceptance Criteria

### 8.1 fetch_edinet_financial_documents.py Success Criteria
- Successfully retrieves securities reports for specified date
- Extracts all available financial metrics from XBRL data
- Generates properly formatted JSON output
- Handles errors gracefully without stopping execution

### 8.2 consolidate_documents.py Success Criteria
- Processes all JSON files in input directory
- Correctly identifies and handles duplicate companies
- Generates consolidated JSON file with latest data
- Maintains data integrity throughout processing

### 8.3 Overall System Success Criteria
- Both tools execute without fatal errors
- Generated JSON files are valid and web-accessible
- Financial data accuracy meets business requirements
- System processes all listed companies within reasonable time