# XBRL Extraction Patterns

## Overview
This document describes common patterns and best practices for extracting financial data from EDINET XBRL documents.

## Key Learnings from Recent Development

### 1. Understanding XBRL Context Structure

XBRL uses contexts to distinguish between different types of financial data:

```xml
<!-- Consolidated data context example -->
<xbrli:context id="CurrentYearDuration_ConsolidatedMember_BusinessResultsOfGroupAxis">
  <!-- Contains consolidated financial data -->
</xbrli:context>

<!-- Individual data context example -->
<xbrli:context id="CurrentYearDuration_NonConsolidatedMember_BusinessResultsOfReportingCompanyAxis">
  <!-- Contains individual (non-consolidated) data -->
</xbrli:context>
```

### 2. Priority-Based Context Selection

When multiple values exist for the same metric, use priority scoring:

```python
def calculate_priority(context_ref):
    priority = 0
    
    # Highest priority for consolidated group results
    if 'BusinessResultsOfGroup' in context_ref:
        priority += 50
    
    # Penalty for individual company results
    if 'ReportingCompany' in context_ref:
        priority -= 30
    
    # Current year data preferred
    if 'CurrentYear' in context_ref:
        priority += 15
    
    return priority
```

### 3. Dynamic Search Pattern

When standard patterns fail, use dynamic search with careful filtering:

```python
def dynamic_search_metric(root, keywords):
    candidates = []
    
    for elem in root.iter():
        if elem.tag and elem.text:
            # Check if tag matches keywords
            if any(keyword in elem.tag for keyword in keywords):
                context_ref = elem.get('contextRef', '')
                
                # Skip individual data if consolidated exists
                if has_consolidated and 'ReportingCompany' in context_ref:
                    continue
                
                # Calculate priority and collect candidate
                priority = calculate_priority(context_ref)
                candidates.append((value, priority))
    
    # Return highest priority match
    return max(candidates, key=lambda x: x[1])[0] if candidates else None
```

### 4. Handling Companies Without Consolidated Statements

Some companies only have individual financial statements:

```python
def should_use_non_consolidated(root):
    # Check if company has consolidated data
    if not _has_consolidated_data(root):
        # Use NonConsolidatedMember data for current year only
        return True
    return False
```

### 5. Common Pitfalls and Solutions

#### Pitfall 1: Mixing Consolidated and Individual Data
**Problem**: Getting employee count from individual data while other metrics from consolidated.
**Solution**: Consistent context checking across all metrics.

#### Pitfall 2: Ignoring Context Hierarchy
**Problem**: Treating all contexts equally.
**Solution**: Implement priority scoring system.

#### Pitfall 3: Hard-coding Pattern Exclusions
**Problem**: Always excluding NonConsolidatedMember.
**Solution**: Conditional logic based on data availability.

## Best Practices

1. **Always Check for Consolidated Data First**
   ```python
   has_consolidated = _has_consolidated_data(root)
   ```

2. **Use Consistent Priority Scoring**
   - BusinessResultsOfGroup: +50 points
   - ConsolidatedMember: +30 points
   - ReportingCompany: -30 points
   - NonConsolidatedMember: -20 points

3. **Implement Fallback Mechanisms**
   - Try standard patterns first
   - Use dynamic search as fallback
   - Log when using fallback methods

4. **Validate Extracted Values**
   - Check for reasonable ranges
   - Compare related metrics for consistency
   - Log suspicious values for review

## Testing Strategies

1. **Test with Various Company Types**
   - Large corporations with consolidated statements
   - Small companies with only individual statements
   - Financial institutions with special reporting

2. **Verify Context Handling**
   - Ensure consolidated data is prioritized
   - Confirm fallback to individual data when needed
   - Check that historical data is properly filtered

3. **Edge Case Testing**
   - Companies with complex group structures
   - Companies transitioning between reporting types
   - Special industry reporting requirements