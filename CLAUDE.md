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

The system now uses a modular architecture with shared utilities in the `lib/` directory:
- `lib/edinet_common.py`: Core utilities including API configuration, XBRL namespaces, logging setup, and data validation functions
- `lib/xbrl_parser.py`: Specialized XBRL document extraction and financial metrics parsing
- Main scripts import from the lib module for consistent functionality across tools

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
- Extract available metrics: netSales, employees, operatingIncome, equity
- Calculate derived metrics: operatingIncomeRate, ebitda, ebitdaMargin

## Technical Implementation Guidelines

### XBRL Processing Standards
- Target taxonomy: EDINET 2024-11-01
- Use specific namespace mappings for reliable data extraction
- Handle XBRL parsing errors gracefully (continue with other companies)

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

