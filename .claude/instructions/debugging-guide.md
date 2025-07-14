# Debugging Guide

## Common Issues and Solutions

### 1. Individual Data Being Extracted Instead of Consolidated

#### Symptoms
- Employee count significantly lower than expected
- Financial metrics don't match company scale
- Mixed data types in single company record

#### Debugging Steps
1. Check if company has consolidated data:
   ```python
   has_consolidated = _has_consolidated_data(root)
   print(f"Has consolidated data: {has_consolidated}")
   ```

2. Examine context references:
   ```python
   for elem in root.iter():
       if elem.text and 'Employee' in elem.tag:
           print(f"Tag: {elem.tag}")
           print(f"Context: {elem.get('contextRef')}")
           print(f"Value: {elem.text}")
   ```

3. Verify context filtering:
   - Check if ReportingCompany contexts are being skipped
   - Ensure BusinessResultsOfGroup contexts are prioritized

#### Common Fixes
- Update context priority scoring
- Add missing context patterns to filter
- Ensure consistent filtering across all metrics

### 2. Missing Data for Non-consolidated Companies

#### Symptoms
- Companies return no data
- All financial metrics are null
- Extraction succeeds but with empty results

#### Debugging Steps
1. Check consolidated data detection:
   ```python
   # Should return False for non-consolidated only companies
   if _has_consolidated_data(root):
       print("ERROR: Incorrectly detected as having consolidated data")
   ```

2. Verify NonConsolidatedMember handling:
   ```python
   # Should include NonConsolidatedMember when no consolidated exists
   if not has_consolidated and 'NonConsolidatedMember' in skip_list:
       print("ERROR: Incorrectly filtering NonConsolidatedMember")
   ```

### 3. Incorrect Priority Calculation

#### Symptoms
- Wrong data selected despite correct data being available
- Priority scoring not working as expected

#### Debugging Steps
1. Add priority logging:
   ```python
   def _calculate_priority_with_logging(tag_name, context_ref, value):
       priority = _calculate_priority(tag_name, context_ref, value)
       logger.debug(f"Priority calculation:")
       logger.debug(f"  Tag: {tag_name}")
       logger.debug(f"  Context: {context_ref}")
       logger.debug(f"  Score: {priority}")
       return priority
   ```

2. Compare all candidates:
   ```python
   # Log all candidates before selection
   for value, priority, tag, context in candidates:
       logger.debug(f"Candidate: {tag} = {value} (priority: {priority})")
   ```

### 4. XBRL Parsing Errors

#### Symptoms
- Extraction fails with parsing errors
- Malformed XML exceptions
- Namespace errors

#### Debugging Steps
1. Validate XBRL structure:
   ```python
   try:
       root = ET.fromstring(xbrl_content)
   except ET.ParseError as e:
       print(f"Parse error: {e}")
       print(f"Content sample: {xbrl_content[:500]}")
   ```

2. Check namespace handling:
   ```python
   # Verify namespaces are correctly defined
   for prefix, uri in XBRL_NAMESPACES.items():
       elements = root.findall(f'.//{prefix}:*', XBRL_NAMESPACES)
       print(f"{prefix}: {len(elements)} elements found")
   ```

## Performance Debugging

### Slow Extraction
1. Profile extraction time per company
2. Check for inefficient XPath queries
3. Verify API rate limiting is not too conservative

### Memory Issues
1. Monitor memory usage during large batch processing
2. Ensure proper cleanup of parsed XML trees
3. Check for memory leaks in long-running processes

## Logging Best Practices

### Enable Debug Logging
```bash
# Set log level to DEBUG for detailed output
export LOG_LEVEL=DEBUG
python bin/fetch_edinet_financial_documents.py ...
```

### Analyze Log Patterns
```bash
# Find all context references
grep "contextRef" fetch_*.log | sort | uniq -c

# Check for specific errors
grep -i "error\|warning" fetch_*.log

# Track extraction success rate
grep "Successfully extracted" fetch_*.log | wc -l
```

## Testing Strategies

### 1. Unit Test Individual Components
```python
def test_has_consolidated_data():
    # Test with known consolidated company
    xbrl_consolidated = load_test_xbrl('consolidated_company.xml')
    assert _has_consolidated_data(xbrl_consolidated) == True
    
    # Test with non-consolidated only company
    xbrl_individual = load_test_xbrl('individual_company.xml')
    assert _has_consolidated_data(xbrl_individual) == False
```

### 2. Integration Test with Real Data
```python
# Test specific companies with known characteristics
test_companies = [
    ('7203', 'consolidated', {'min_employees': 300000}),
    ('1401', 'individual', {'max_employees': 1000}),
]
```

### 3. Regression Testing
- Keep test data from problematic companies
- Run tests after any extraction logic changes
- Verify no regressions in previously fixed issues