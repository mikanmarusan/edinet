# Architecture

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

### Module Dependencies
```
bin/fetch_edinet_financial_documents.py
├── lib/edinet_common.py
│   ├── API configuration (API_BASE_URL, RETRY_DELAYS)
│   ├── XBRL namespaces (NAMESPACES)
│   ├── Logging setup (setup_logging)
│   └── Utility functions (fetch_document_list, format_date)
└── lib/xbrl_parser.py
    ├── XBRLParser class
    ├── extract_financial_metrics()
    └── Dynamic search algorithms

bin/consolidate_documents.py
└── lib/edinet_common.py
    ├── Logging setup (setup_logging)
    └── Utility functions (load_json_file)
```

### Design Principles

#### Separation of Concerns
- **Presentation Layer**: Command-line scripts in bin/
- **Business Logic**: Core functionality in lib/
- **Data Layer**: JSON file I/O operations

#### Error Handling Strategy
- **Fail-Safe Operation**: Individual document failures don't stop the entire process
- **Comprehensive Logging**: All errors are logged with context
- **Graceful Degradation**: Missing data fields are set to null rather than causing exceptions

#### Performance Considerations
- **Memory Efficiency**: Process documents one at a time to avoid memory issues
- **I/O Optimization**: Batch file operations where possible
- **API Rate Limiting**: Built-in delays to comply with EDINET restrictions

### Extension Points
- **New Data Sources**: Add new parser modules in lib/
- **Additional Metrics**: Extend XBRLParser.extract_financial_metrics()
- **Output Formats**: Add formatters alongside JSON output
- **Storage Backends**: Replace file I/O with database operations

### XBRL Data Extraction Strategy

#### Consolidated vs Non-Consolidated Financial Statements
- **Priority**: Always prefer consolidated financial data when available
- **Fallback**: Use non-consolidated data only when consolidated data doesn't exist
- **Implementation**:
  - `_has_consolidated_data()` method checks for presence of consolidated contexts
  - All extraction methods conditionally include/exclude NonConsolidatedMember
  - Historical data (PriorYear contexts) is always excluded for non-consolidated data
  
#### Context Priority System (2025-07 Update)
- **Highest Priority**: BusinessResultsOfGroup contexts (+50~80 points)
- **High Priority**: ConsolidatedMember contexts (+30~55 points)
- **Standard Priority**: CurrentYear contexts (+15 points)
- **Penalties**: 
  - ReportingCompany contexts: -30 points (individual data)
  - NonConsolidatedMember: -20 points

#### Context Filtering Logic
```python
# Pseudo-code for context filtering
if has_consolidated_data:
    # Traditional behavior - exclude NonConsolidatedMember
    valid_contexts = [c for c in contexts if 'NonConsolidatedMember' not in c]
    # NEW: Also skip ReportingCompany contexts when consolidated data exists
    valid_contexts = [c for c in valid_contexts if 'ReportingCompany' not in c]
else:
    # New behavior - include NonConsolidatedMember for current year only
    valid_contexts = [c for c in contexts if 'CurrentYear' in c]
```

#### Key XBRL Context Patterns
- **BusinessResultsOfGroup**: Most reliable indicator of consolidated data
- **ReportingCompany**: Indicates individual/non-consolidated data
- **ConsolidatedMember**: Explicit consolidated data marker
- **NonConsolidatedMember**: Explicit non-consolidated data marker

#### Affected Methods
- `extract_numeric_value_with_context`: Core extraction method with conditional logic
- `_dynamic_search_*`: All dynamic search methods check consolidated data availability
- Priority calculation methods: `_calculate_*_priority()` for consistent scoring
- Pattern matching maintains backward compatibility for companies with consolidated data