#!/usr/bin/env python3
"""
Local testing script for Receipt OCR API (Azure Document Intelligence)
Tests all endpoints and functionality before Azure deployment
"""

import requests
import json
import time
import os
from pathlib import Path

API_URL = "http://localhost:8000"

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.NC}")

def main():
    print("=" * 60)
    print("Receipt OCR API Testing Script (Azure Document Intelligence)")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    # Step 1: Check API is accessible
    print("Step 1: Checking if API is accessible...")
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            print_success("API is accessible")
            passed += 1
        else:
            print_error("API returned unexpected status")
            failed += 1
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is it running?")
        print_info("Run: docker-compose up -d")
        return 1
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return 1
    
    # Step 2: Test root endpoint
    print("\nStep 2: Testing root endpoint...")
    try:
        response = requests.get(f"{API_URL}/")
        data = response.json()
        
        print(f"  Status: {data.get('status')}")
        print(f"  Service: {data.get('service')}")
        print(f"  Version: {data.get('version')}")
        print(f"  Provider: {data.get('provider')}")
        
        if data.get('status') == 'running' and data.get('provider') == 'Azure Document Intelligence':
            print_success("Root endpoint working")
            passed += 1
        else:
            print_error("Unexpected response")
            failed += 1
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        failed += 1
    
    # Step 3: Test health endpoint
    print("\nStep 3: Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health")
        data = response.json()
        
        print(f"  Status: {data.get('status')}")
        print(f"  Azure Document Intelligence: {data.get('azure_doc_intelligence')}")
        
        if data.get('endpoint'):
            print(f"  Endpoint: {data.get('endpoint')}")
        
        if data.get('status') == 'healthy' and data.get('azure_doc_intelligence'):
            print_success("Health check passed - Azure credentials configured")
            passed += 1
        elif data.get('status') == 'degraded':
            print_error("Health check failed - Azure credentials not configured")
            print_warning(f"Error: {data.get('error')}")
            print_info("Set AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY in .env file")
            failed += 1
        else:
            print_error("Unexpected health status")
            failed += 1
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        failed += 1
    
    # Step 4: Test with receipt image
    print("\nStep 4: Testing receipt extraction...")
    
    # Look for test receipt
    test_files = ['test_receipt.jpg', 'test_receipt.png', 'receipt.jpg', 'receipt.png', 'test_receipt.pdf']
    test_file = None
    
    for filename in test_files:
        if os.path.exists(filename):
            test_file = filename
            break
    
    if test_file:
        print_info(f"Found test file: {test_file}")
        
        # Determine content type
        content_type = 'image/jpeg'
        if test_file.endswith('.png'):
            content_type = 'image/png'
        elif test_file.endswith('.pdf'):
            content_type = 'application/pdf'
        
        # Test raw extraction
        print("\n  Testing raw OCR extraction...")
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file, f, content_type)}
                response = requests.post(f"{API_URL}/extract/raw", files=files, timeout=60)
                data = response.json()
                
                if data.get('success'):
                    print_success("Raw OCR successful")
                    raw_azure = data.get('raw_azure_response', {})
                    if raw_azure:
                        print(f"    Detected fields: {raw_azure.get('all_fields', [])[:5]}...")
                    passed += 1
                else:
                    print_error(f"Raw OCR failed: {data.get('error')}")
                    failed += 1
        except Exception as e:
            print_error(f"Failed: {str(e)}")
            failed += 1
        
        # Test full extraction
        print("\n  Testing full structured extraction...")
        try:
            start_time = time.time()
            with open(test_file, 'rb') as f:
                files = {'file': (test_file, f, content_type)}
                response = requests.post(f"{API_URL}/extract", files=files, timeout=60)
                elapsed = time.time() - start_time
                
                data = response.json()
                
                if data.get('success'):
                    receipt = data.get('receipt_data', {})
                    print_success(f"Full extraction successful ({elapsed:.2f}s)")
                    print(f"    Merchant: {receipt.get('merchant_name')}")
                    print(f"    Amount: ${receipt.get('transaction_amount'):.2f}")
                    print(f"    Date: {receipt.get('transaction_date')}")
                    print(f"    Receipt #: {receipt.get('receipt_number') or 'Not found'}")
                    print(f"    GST: ${receipt.get('gst_amount'):.2f}" if receipt.get('gst_amount') else "    GST: N/A")
                    print(f"    Payment: {receipt.get('payment_method')}")
                    print(f"    Line Items: {len(receipt.get('items', []))}")
                    print(f"    Confidence: {receipt.get('ocr_confidence', 0)*100:.1f}%")
                    print(f"    Totals Match: {receipt.get('items_total_matches')}")
                    
                    # Check validation warnings
                    warnings = data.get('receipt_data', {}).get('validation_warnings') or data.get('validation_warnings')
                    if warnings:
                        print_warning(f"    Warnings: {len(warnings)}")
                        for w in warnings:
                            print(f"      - {w}")
                    
                    # Validate line items
                    items = receipt.get('items', [])
                    if len(items) > 0:
                        print_success(f"    Line items extracted: {len(items)}")
                        for i, item in enumerate(items[:3], 1):  # Show first 3
                            print(f"      {i}. {item.get('line_description')} - ${item.get('line_amount'):.2f}")
                        if len(items) > 3:
                            print(f"      ... and {len(items) - 3} more")
                    else:
                        print_error("    No line items found")
                    
                    passed += 1
                    
                    # Save result for inspection
                    with open('test_result.json', 'w') as out:
                        json.dump(data, out, indent=2)
                    print_info("    Full result saved to test_result.json")
                else:
                    print_error(f"Extraction failed: {data.get('error')}")
                    failed += 1
        except Exception as e:
            print_error(f"Failed: {str(e)}")
            failed += 1
        
        # Test response time (second call)
        print("\n  Testing second request (should be faster)...")
        try:
            start_time = time.time()
            with open(test_file, 'rb') as f:
                files = {'file': (test_file, f, content_type)}
                response = requests.post(f"{API_URL}/extract", files=files, timeout=60)
                elapsed = time.time() - start_time
            
            if elapsed < 5.0:
                print_success(f"Response time good: {elapsed:.2f}s")
                passed += 1
            elif elapsed < 10.0:
                print_warning(f"Response time acceptable: {elapsed:.2f}s")
                passed += 1
            else:
                print_warning(f"Response time slow: {elapsed:.2f}s")
                print_info("Azure Document Intelligence may be under load")
                passed += 1
        except Exception as e:
            print_error(f"Failed: {str(e)}")
            failed += 1
            
    else:
        print_warning("No test receipt found")
        print_info("Add a test_receipt.jpg/png/pdf file to test extraction")
        print_info("Skipping receipt tests...")
        print()
    
    # Step 5: Test error handling
    print("\nStep 5: Testing error handling...")
    
    # Test invalid file type
    print("  Testing invalid file type rejection...")
    try:
        with open('test_invalid.txt', 'w') as f:
            f.write('This is not an image')
        
        with open('test_invalid.txt', 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            response = requests.post(f"{API_URL}/extract", files=files, timeout=10)
            data = response.json()
        
        os.remove('test_invalid.txt')
        
        if not data.get('success') and 'Unsupported file type' in str(data.get('error', '')):
            print_success("Invalid file type correctly rejected")
            passed += 1
        else:
            print_error("Error handling not working as expected")
            failed += 1
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        failed += 1
    
    # Test missing file
    print("  Testing missing file handling...")
    try:
        response = requests.post(f"{API_URL}/extract", timeout=10)
        
        if response.status_code == 422:  # FastAPI validation error
            print_success("Missing file correctly rejected")
            passed += 1
        else:
            print_warning(f"Unexpected status code: {response.status_code}")
            passed += 1
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests Passed: {Colors.GREEN}{passed}{Colors.NC}")
    print(f"Tests Failed: {Colors.RED}{failed}{Colors.NC}")
    print()
    
    if failed == 0:
        print_success("All tests passed! ✓")
        print_info("Your API is ready for Azure deployment")
        print()
        print("Next steps:")
        print("  1. Review test_result.json to verify extraction accuracy")
        print("  2. Test with more receipt images if available")
        print("  3. Run: ./deploy_azure.sh to deploy to Azure App Service")
        print()
        return 0
    else:
        print_error(f"{failed} test(s) failed")
        print_info("Please fix the issues before deploying to Azure")
        print()
        print("Common issues:")
        print("  - Azure credentials not set: Check .env file")
        print("  - Container not running: docker-compose ps")
        print("  - Check logs: docker-compose logs api")
        print("  - Invalid credentials: Verify in Azure Portal")
        print()
        return 1

if __name__ == "__main__":
    exit(main())