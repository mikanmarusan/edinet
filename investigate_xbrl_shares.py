#!/usr/bin/env python3
"""
XBRL Share Tag Investigation Tool

Investigates XBRL documents to find share-related tags that could be used 
for extracting outstanding shares information.
"""

import requests
import json
import time
import zipfile
import io
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sys

# EDINET API configuration
EDINET_BASE_URL = "https://disclosure.edinet-fsa.go.jp/api/v2"
RATE_LIMIT_DELAY = 1.0

class XBRLShareInvestigator:
    """Investigates share-related tags in XBRL documents"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Ocp-Apim-Subscription-Key': api_key})
    
    def download_xbrl_document(self, doc_id: str) -> Optional[bytes]:
        """Download XBRL document from EDINET"""
        try:
            url = f"{EDINET_BASE_URL}/documents/{doc_id}?type=5"
            print(f"Downloading XBRL for {doc_id}...")
            
            response = self.session.get(url, timeout=60)
            time.sleep(RATE_LIMIT_DELAY)
            
            if response.status_code == 200:
                # Check if response is JSON (error) or binary (ZIP)
                try:
                    error_data = response.json()
                    print(f"API Error: {error_data}")
                    return None
                except:
                    # Not JSON, should be ZIP content
                    return response.content
            else:
                print(f"HTTP Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error downloading {doc_id}: {e}")
            return None
    
    def extract_xbrl_from_zip(self, zip_content: bytes) -> Optional[bytes]:
        """Extract main XBRL file from ZIP archive"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_file:
                xbrl_files = [f for f in zip_file.namelist() if f.endswith(('.xbrl', '.xml'))]
                
                # Priority: main XBRL instance file
                for filename in xbrl_files:
                    if ('PublicDoc' in filename and filename.endswith('.xbrl') and 
                        'jpcrp030000-asr' in filename):
                        return zip_file.read(filename)
                
                # Fallback: any XBRL file in PublicDoc
                for filename in xbrl_files:
                    if 'PublicDoc' in filename and filename.endswith('.xbrl'):
                        return zip_file.read(filename)
                
                # Last resort: any XBRL file
                if xbrl_files:
                    return zip_file.read(xbrl_files[0])
                    
        except Exception as e:
            print(f"Error extracting XBRL from ZIP: {e}")
        
        return None
    
    def find_share_related_tags(self, xbrl_content: bytes) -> List[Tuple[str, str, str]]:
        """Find all share-related tags in XBRL document"""
        try:
            root = ET.fromstring(xbrl_content)
            share_tags = []
            
            # Keywords to search for
            share_keywords = [
                'Share', 'Stock', 'Issued', 'Outstanding', 'Capital',
                '株式', '発行', '株数', 'NumberOf', 'Shares'
            ]
            
            # Search through all elements
            for elem in root.iter():
                if elem.tag:
                    tag_name = elem.tag
                    
                    # Check if tag contains share-related keywords
                    for keyword in share_keywords:
                        if keyword.lower() in tag_name.lower():
                            value = elem.text.strip() if elem.text else ""
                            context_ref = elem.get('contextRef', '')
                            
                            # Try to parse as number to filter numeric values
                            try:
                                if value:
                                    numeric_value = float(value.replace(',', ''))
                                    if numeric_value > 0:  # Only positive values
                                        share_tags.append((tag_name, value, context_ref))
                            except ValueError:
                                # Not a number, might still be relevant
                                if len(value) < 100:  # Avoid very long text
                                    share_tags.append((tag_name, value, context_ref))
                            break
            
            return share_tags
            
        except Exception as e:
            print(f"Error parsing XBRL content: {e}")
            return []
    
    def investigate_document(self, doc_id: str, company_name: str) -> Dict[str, any]:
        """Investigate a single document for share-related information"""
        print(f"\n{'='*60}")
        print(f"Investigating: {company_name} ({doc_id})")
        print(f"{'='*60}")
        
        # Download XBRL
        zip_content = self.download_xbrl_document(doc_id)
        if not zip_content:
            return {"error": "Failed to download XBRL"}
        
        # Extract main XBRL file
        xbrl_content = self.extract_xbrl_from_zip(zip_content)
        if not xbrl_content:
            return {"error": "Failed to extract XBRL from ZIP"}
        
        # Find share-related tags
        share_tags = self.find_share_related_tags(xbrl_content)
        
        # Organize results
        results = {
            "company": company_name,
            "doc_id": doc_id,
            "share_tags_found": len(share_tags),
            "share_tags": share_tags[:20]  # Limit output
        }
        
        # Print results
        print(f"Found {len(share_tags)} share-related tags:")
        for i, (tag, value, context) in enumerate(share_tags[:20]):
            print(f"  {i+1:2d}. {tag}")
            print(f"      Value: {value}")
            print(f"      Context: {context}")
            print()
        
        if len(share_tags) > 20:
            print(f"... and {len(share_tags) - 20} more tags")
        
        return results


def main():
    """Main investigation function"""
    # Load recent document data
    try:
        with open('data/jsons/2025-06-18.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
    except FileNotFoundError:
        print("Error: Could not find data/jsons/2025-06-18.json")
        print("Please run fetch_edinet_financial_documents.py first")
        return
    
    # Initialize investigator
    investigator = XBRLShareInvestigator()
    
    # Investigate a few companies
    investigation_results = []
    companies_to_investigate = companies[:3]  # Investigate first 3 companies
    
    for company in companies_to_investigate:
        result = investigator.investigate_document(
            company['docID'], 
            company['filerName']
        )
        investigation_results.append(result)
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    # Summary
    print(f"\n{'='*60}")
    print("INVESTIGATION SUMMARY")
    print(f"{'='*60}")
    
    all_tags = {}
    for result in investigation_results:
        if 'share_tags' in result:
            for tag, value, context in result['share_tags']:
                tag_name = tag.split('}')[-1] if '}' in tag else tag  # Remove namespace
                if tag_name not in all_tags:
                    all_tags[tag_name] = []
                all_tags[tag_name].append((result['company'], value, context))
    
    print(f"Unique share-related tag names found across all companies:")
    for i, (tag_name, occurrences) in enumerate(sorted(all_tags.items())):
        print(f"  {i+1:2d}. {tag_name} (found in {len(occurrences)} companies)")
        for company, value, context in occurrences[:2]:  # Show first 2 examples
            print(f"      {company}: {value} ({context[:30]}...)")
        if len(occurrences) > 2:
            print(f"      ... and {len(occurrences) - 2} more")
        print()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"xbrl_share_investigation_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "investigation_date": datetime.now().isoformat(),
            "summary": {
                "companies_investigated": len(investigation_results),
                "unique_tags_found": len(all_tags),
                "tag_summary": {tag: len(occs) for tag, occs in all_tags.items()}
            },
            "detailed_results": investigation_results,
            "all_tags": {tag: occs for tag, occs in all_tags.items()}
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Detailed results saved to: {results_file}")
    
    # Recommendations
    print(f"\n{'='*60}")  
    print("RECOMMENDATIONS FOR OUTSTANDING SHARES EXTRACTION")
    print(f"{'='*60}")
    
    # Look for the most promising tags
    promising_tags = []
    for tag_name, occurrences in all_tags.items():
        if any(keyword in tag_name.lower() for keyword in ['issued', 'outstanding', 'shares', 'stock']):
            if any(keyword in tag_name.lower() for keyword in ['number', 'share']):
                promising_tags.append((tag_name, len(occurrences)))
    
    if promising_tags:
        print("Most promising tags for outstanding shares:")
        for tag, count in sorted(promising_tags, key=lambda x: x[1], reverse=True):
            print(f"  - {tag} (found in {count} companies)")
            # Create XBRL pattern
            print(f"    Suggested pattern: './/jpcrp_cor:{tag}' or './/jppfs_cor:{tag}'")
    else:
        print("No obvious outstanding shares tags found in the sample.")
        print("Consider expanding the search or checking different document types.")


if __name__ == "__main__":
    main()