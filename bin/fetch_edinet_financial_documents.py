#!/usr/bin/env python3
"""
EDINET Daily Data Extraction Tool

Retrieves securities reports submitted on a specific date via EDINET API,
parses XBRL data, and extracts predefined financial metrics.

Usage:
    python bin/fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY
"""

import argparse
import json
import sys
import time
import os
from typing import List, Dict, Any, Optional
import requests

# Add parent directory to path to access lib module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.edinet_common import (
    EDINET_BASE_URL, RATE_LIMIT_DELAY, DEFAULT_TIMEOUT, DOWNLOAD_TIMEOUT,
    setup_logging, validate_date_format, normalize_securities_code,
    ensure_output_directory, EdinetAPIError
)
from lib.xbrl_parser import XBRLParser


class EdinetClient:
    """Client for interacting with EDINET API v2"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0
        
    def _wait_for_rate_limit(self):
        """Ensure rate limit compliance"""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def get_documents(self, date: str) -> List[Dict[str, Any]]:
        """
        Retrieve list of documents submitted on specified date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of document metadata
        """
        self._wait_for_rate_limit()
        
        url = f"{EDINET_BASE_URL}/documents.json"
        params = {
            "date": date,
            "type": "2"  # Documents to be submitted
        }
        
        if self.api_key:
            params["Subscription-Key"] = self.api_key
            
        try:
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # Filter for documents with docTypeCode=120 and secCode exists
            documents = data.get("results", [])
            securities_reports = [
                doc for doc in documents
                if doc.get("docTypeCode") == "120" and doc.get("secCode")
            ]
            
            return securities_reports
            
        except requests.exceptions.RequestException as e:
            raise EdinetAPIError(f"Error fetching documents: {e}")
    
    def download_document(self, doc_id: str) -> Optional[bytes]:
        """
        Download XBRL document by document ID
        
        Args:
            doc_id: Document ID from EDINET
            
        Returns:
            Document content as bytes or None if error
        """
        self._wait_for_rate_limit()
        
        url = f"{EDINET_BASE_URL}/documents/{doc_id}"
        params = {"type": "1"}  # XBRL format
        
        if self.api_key:
            params["Subscription-Key"] = self.api_key
            
        try:
            response = self.session.get(url, params=params, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            raise EdinetAPIError(f"Error downloading document {doc_id}: {e}")

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


def main():
    """Main entry point for EDINET data extraction"""
    parser = argparse.ArgumentParser(description="Extract financial data from EDINET for a specific date")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--outputdir", required=True, help="Output directory for JSON files")
    parser.add_argument("--api-key", required=True, help="EDINET API key")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retries for failed requests")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging('fetch_edinet_financial_documents', args.verbose)
    
    logger.info(f"Starting EDINET data extraction for date: {args.date}")
    
    # Validate date format
    if not validate_date_format(args.date):
        logger.error("Date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    try:
        # Initialize clients
        edinet_client = EdinetClient(args.api_key)
        xbrl_parser = XBRLParser()
        
        logger.info(f"Retrieving securities reports for {args.date}...")
        
        # Get list of securities reports for the date
        try:
            documents = edinet_client.get_documents(args.date)
        except EdinetAPIError as e:
            logger.error(f"Failed to fetch documents: {e}")
            sys.exit(1)
        
        if not documents:
            logger.warning(f"No securities reports found for {args.date}")
            return
        
        logger.info(f"Found {len(documents)} securities reports")
        
        # Process each document
        financial_data_list = []
        successful_extractions = 0
        failed_extractions = 0
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get("docID", "")
            sec_code = doc.get("secCode", "")
            # Normalize securities code to 4 digits
            sec_code = normalize_securities_code(sec_code)
            filer_name = doc.get("filerName", "")
            period_end = doc.get("periodEnd", "")
            
            logger.info(f"Processing [{i}/{len(documents)}] {filer_name} ({sec_code})...")
            
            retry_count = 0
            success = False
            
            while retry_count < args.max_retries and not success:
                try:
                    # Download XBRL document
                    try:
                        xbrl_content = edinet_client.download_document(doc_id)
                    except EdinetAPIError as e:
                        logger.warning(f"Failed to download document for {filer_name} ({sec_code}): {e}")
                        break
                    
                    # Parse financial data
                    financial_data = xbrl_parser.parse_financial_data(xbrl_content, sec_code, filer_name, doc_id, period_end)
                    if financial_data:
                        financial_data_list.append(financial_data)
                        logger.info(f"Successfully extracted data for {filer_name}")
                        successful_extractions += 1
                        success = True
                    else:
                        logger.warning(f"Failed to parse XBRL data for {filer_name} ({sec_code})")
                        break
                        
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error processing {filer_name} ({sec_code}) - attempt {retry_count}: {e}")
                    
                    if retry_count < args.max_retries:
                        logger.info(f"Retrying in 2 seconds...")
                        time.sleep(2)
                    else:
                        logger.error(f"Max retries exceeded for {filer_name} ({sec_code})")
            
            if not success:
                failed_extractions += 1
        
        # Save results to JSON file
        try:
            if not ensure_output_directory(args.outputdir):
                raise Exception("Failed to create output directory")
                
            output_file = f"{args.outputdir}/{args.date}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(financial_data_list, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(financial_data_list)} company records to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results to file: {e}")
            sys.exit(1)
        
        # Summary
        logger.info(f"Extraction completed!")
        logger.info(f"  Total documents processed: {len(documents)}")
        logger.info(f"  Successful extractions: {successful_extractions}")
        logger.info(f"  Failed extractions: {failed_extractions}")
        logger.info(f"  Output file: {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()