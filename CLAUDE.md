# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **edinet** project - a tool for retrieving Listed Company Disclosures from EDINET (Electronic Disclosure for Investors' NETwork), which is Japan's electronic disclosure system for corporate information.

## Current State

This repository contains a functional EDINET financial data extraction system:
- `fetch_edinet_financial_documents.py`: Daily data extraction tool
- `consolidate_documents.py`: Data consolidation tool
- `requirements.txt`: Python dependencies
- Complete documentation and specification files

## Development Notes

The project consists of two main command-line tools for EDINET financial data extraction and consolidation:
- `fetch_edinet_financial_documents.py`: Daily data extraction from EDINET API
- `consolidate_documents.py`: Data consolidation from multiple daily files

### Modular Architecture

The system has been refactored to use a modular architecture with shared utilities in the `lib/` directory:

- **lib/edinet_common.py**: Contains shared API configuration, XBRL namespace mappings, logging setup, and common utility functions used by both main scripts
- **lib/xbrl_parser.py**: Dedicated XBRL document parsing and financial metrics extraction functionality 
- **lib/__init__.py**: Module initialization for the shared library

This modularization improves code maintainability, reduces duplication, and provides a clean separation of concerns between shared utilities and main application logic.

## Tool Design Principles

### Command-Line Interface Standards
- All required parameters must be explicitly specified (no defaults for critical paths)
- Use descriptive parameter names that clearly indicate purpose:
  - `--inputdir` / `--outputdir` instead of generic `--input` / `--output`
  - `--api-key` as required parameter for security transparency
- Implement consistent logging patterns across all tools

### Error Handling Philosophy
- Fail gracefully: continue processing other items when individual items fail
- Comprehensive logging: both console and file output for debugging
- Rate limiting compliance: respect external API constraints (1 req/sec for EDINET)

## Data Quality Standards

### Data Format Consistency
- Japanese date format: YYYY年MM月期 (no leading zeros for single-digit months)
- Securities codes: 4-digit format (remove trailing zero from 5-digit codes)
- Null handling: Explicitly set unavailable fields to null rather than omitting

### EDINET-Focused Data Strategy
- Primary data source: EDINET XBRL data
- Focus on reliable, verifiable financial data from official sources
- Extract available metrics: netSales, employees, operatingIncome, equity, netIncome, outstandingShares, eps, cash, bps, debt
- Calculate derived metrics: operatingIncomeRate, ebitda, ebitdaMargin, ev, evPerEbitda
- Advanced extraction: Dynamic search algorithms for PER, EPS, outstanding shares, cash, BPS, and debt when standard patterns fail

## Technical Implementation Guidelines

### XBRL Processing Standards
- Target taxonomy: EDINET 2024-11-01
- Use specific namespace mappings for reliable data extraction
- Handle XBRL parsing errors gracefully (continue with other companies)

### Advanced XBRL Processing Features
- **Dynamic Search Algorithms**: When standard XBRL patterns fail, implement sophisticated fallback mechanisms
- **Context Prioritization**: Use XBRL context references to prioritize current year data over historical
- **Consolidated Data Priority**: Systematically exclude NonConsolidatedMember contexts to prioritize consolidated financial data
- **Priority Scoring**: Calculate priority scores for data candidates to select the most relevant values
- **Range Validation**: Filter unreasonable values to ensure data quality (e.g., PER < 1000, share counts in reasonable ranges)
- **Multi-Pattern Extraction**: Support multiple extraction strategies for robust data capture across different company reporting formats
- **Period-End Prioritization**: For cash and time-sensitive metrics, prioritize end-of-period data over other temporal contexts

### File Organization
- Descriptive filenames: `fetch_edinet_financial_documents.py`, `consolidate_documents.py`
- Structured output: `{outputdir}/{YYYY-MM-DD}.json` pattern
- Log files: `{script_name}_{YYYYMMDD}.log` pattern

### API Integration Best Practices
- Mandatory API key parameter for accountability
- Implement proper rate limiting (1 second delays)
- Robust retry mechanisms with exponential backoff

## Development Lessons Learned

### Command-Line Tool Evolution
- Initial optional parameters led to unclear execution contexts
- Solution: Make critical parameters (outputdir, api-key) mandatory
- Benefit: More predictable and secure tool behavior

### Data Consolidation Strategy
- Latest data precedence for duplicate companies
- Explicit output path specification prevents accidental overwrites
- Summary reporting for data quality verification

### XBRL Data Processing
- periodEnd format standardization improves data consistency
- Securities code normalization (4-digit) ensures uniform identification
- Robust namespace handling essential for reliable XBRL parsing
- Consolidated vs individual data distinction critical for accurate financial metrics
- Dynamic search patterns significantly improve extraction success rates (e.g., netIncome: 40% → 100%)

### Recent Enhancement Learnings (2025-06-22)
- **Consolidated Data Prioritization**: Root cause of data extraction issues was NonConsolidatedMember contexts being included
- **Dynamic Search Success**: Implementing comprehensive keyword-based fallback mechanisms dramatically improves metric extraction rates
- **Cash and Cash Equivalents**: Successfully implemented with period-end prioritization and consolidated data preference
- **Context Hierarchy**: Established priority order: Consolidated+CurrentYear > CurrentYear > Consolidated > Others
- **Field Positioning**: New financial metrics should be positioned before retrievedDate field in JSON structure

## Future Development Guidelines

### Maintainability Focus
- Prioritize reliable EDINET data extraction over feature expansion
- Maintain clear separation between data extraction and consolidation tools
- Document all XBRL field mappings for future taxonomy updates

### Extension Considerations
- Any new data sources must meet reliability standards of EDINET
- Consider database integration for large-scale deployments
- Maintain backward compatibility for existing JSON output format

## Product Requirement Document

Refer to the product requirement document located at .ai-rules/edinet_requirements_spec.md 
for building this software.

 to memorize