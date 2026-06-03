# XBRL Taxonomy Notes

## EDINET XBRL Structure Understanding

### Key Learnings from Development

#### 1. Context Structure in EDINET
EDINET uses dimensional reporting to distinguish between different types of financial data:

- **Consolidated vs Non-consolidated**: Distinguished by dimension members
- **Current vs Historical**: Distinguished by period contexts
- **Group vs Individual**: Distinguished by axis references

#### 2. Important Context Patterns

##### BusinessResultsOfGroup
- **Pattern**: `BusinessResultsOfGroupAxis` or `BusinessResultsOfGroupTable`
- **Meaning**: Consolidated financial data for the entire group
- **Priority**: Highest priority for extraction

##### BusinessResultsOfReportingCompany
- **Pattern**: `BusinessResultsOfReportingCompanyAxis` or `BusinessResultsOfReportingCompanyTable`
- **Meaning**: Individual financial data for the reporting company only
- **Priority**: Should be avoided when consolidated data exists

##### ConsolidatedMember
- **Pattern**: `ConsolidatedMember` in context
- **Meaning**: Explicitly marked as consolidated data
- **Priority**: High priority

##### NonConsolidatedMember
- **Pattern**: `NonConsolidatedMember` in context
- **Meaning**: Explicitly marked as non-consolidated data
- **Priority**: Only use when consolidated data doesn't exist

#### 3. Common Pitfalls

1. **Mixing Data Types**: Getting some metrics from consolidated and others from individual
2. **Ignoring Context Hierarchy**: Not prioritizing BusinessResultsOfGroup
3. **Over-filtering**: Excluding all NonConsolidatedMember data even when it's the only data available

#### 4. Best Practices for Context Handling

```python
# Check consolidated data availability first
has_consolidated = _has_consolidated_data(root)

# Apply different filtering based on availability
if has_consolidated:
    # Strict filtering - exclude individual data
    skip_contexts = ['NonConsolidatedMember', 'ReportingCompany']
else:
    # Relaxed filtering - use what's available
    skip_contexts = ['PriorYear']  # Only skip historical
```

#### 5. Financial vs Non-financial Companies

Financial companies often use different terminology:
- **営業収益** (Operating Revenue) instead of **売上高** (Net Sales)
- Special patterns in lib/edinet_common.py handle these differences

#### 6. Dynamic Search Considerations

When standard patterns fail:
1. Search for element tags containing relevant keywords
2. Apply context priority scoring
3. Filter based on consolidated data availability
4. Return highest priority match

#### 7. Data Quality Indicators

Signs of correct data extraction:
- Employee counts in expected ranges
- Financial metrics internally consistent
- All metrics from same context type

Signs of incorrect extraction:
- Employee count too low (likely individual data)
- Mixed consolidated/individual metrics
- Inconsistent financial ratios

## Future Improvements

1. **Company-specific Patterns**: Some companies may need custom extraction logic
2. **Industry-specific Handling**: Different industries use different XBRL patterns
3. **Validation Rules**: Implement cross-metric validation to detect mixed data
4. **Context Logging**: Enhanced logging to debug context selection decisions