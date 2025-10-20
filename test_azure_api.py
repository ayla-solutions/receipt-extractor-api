#!/usr/bin/env python3
"""
Azure App Service API Health Check Script
Tests the deployed Receipt OCR API
"""

import requests
import json
import sys
from pathlib import Path

# Your Azure App Service URL
API_URL = "https://app-expense-receipt-api.azurewebsites.net"

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

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n" + "="*60)
    print("Test 1: Root Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is running!")
            print(f"  Status: {data.get('status')}")
            print(f"  Service: {data.get('service')}")
            print(f"  Version: {data.get('version')}")
            print(f"  Provider: {data.get('provider')}")
            return True
        else:
            print_error(f"Failed with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is it deployed?")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    print("\n" + "="*60)
    print("Test 2: Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            azure_ok = data.get('azure_doc_intelligence')
            
            if status == 'healthy' and azure_ok:
                print_success("Health check passed!")
                print(f"  Status: {status}")
                print(f"  Azure Document Intelligence: {azure_ok}")
                print(f"  Endpoint: {data.get('endpoint')}")
                return True
            else:
                print_warning("Health check returned but not healthy")
                print(f"  Status: {status}")
                print(f"  Azure Doc Intelligence: {azure_ok}")
                print(f"  Error: {data.get('error')}")
                return False
        else:
            print_error(f"Failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_extract_endpoint(test_file=None):
    """Test the extract endpoint with a receipt image"""
    print("\n" + "="*60)
    print("Test 3: Receipt Extraction Endpoint")
    print("="*60)
    
    # Look for test file
    if test_file is None:
        test_files = ['test_receipt.jpg', 'test_receipt.png', 'receipt.jpg', 'receipt.png']
        for filename in test_files:
            if Path(filename).exists():
                test_file = filename
                break
    
    if test_file is None or not Path(test_file).exists():
        print_warning("No test receipt found. Skipping extraction test.")
        print_info("To test extraction, place a receipt image named 'test_receipt.jpg' in this folder")
        return None
    
    print_info(f"Testing with: {test_file}")
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'image/jpeg')}
            response = requests.post(f"{API_URL}/extract", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                receipt = data.get('receipt_data', {})
                print_success("Receipt extraction successful!")
                print(f"  Merchant: {receipt.get('merchant_name')}")
                print(f"  Amount: ${receipt.get('transaction_amount'):.2f}")
                print(f"  Date: {receipt.get('transaction_date')}")
                print(f"  Receipt #: {receipt.get('receipt_number') or 'N/A'}")
                print(f"  Payment: {receipt.get('payment_method')}")
                print(f"  Line Items: {len(receipt.get('items', []))}")
                print(f"  Confidence: {receipt.get('ocr_confidence', 0)*100:.1f}%")
                
                # Save full response
                with open('azure_test_result.json', 'w') as out:
                    json.dump(data, out, indent=2)
                print_info("Full response saved to: azure_test_result.json")
                
                return True
            else:
                print_error(f"Extraction failed: {data.get('error')}")
                return False
        else:
            print_error(f"Failed with status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_invalid_file():
    """Test error handling with invalid file"""
    print("\n" + "="*60)
    print("Test 4: Error Handling (Invalid File)")
    print("="*60)
    
    try:
        # Create a temporary text file
        with open('temp_invalid.txt', 'w') as f:
            f.write('This is not an image')
        
        with open('temp_invalid.txt', 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            response = requests.post(f"{API_URL}/extract", files=files, timeout=10)
        
        # Clean up
        Path('temp_invalid.txt').unlink()
        
        data = response.json()
        if not data.get('success') and 'Unsupported file type' in str(data.get('error', '')):
            print_success("Error handling works correctly!")
            print(f"  Correctly rejected invalid file type")
            return True
        else:
            print_warning("Error handling may not be working as expected")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("Azure Receipt OCR API - Health Check")
    print(f"Testing: {API_URL}")
    print("="*60)
    
    results = {}
    
    # Run all tests
    results['root'] = test_root_endpoint()
    results['health'] = test_health_endpoint()
    results['extract'] = test_extract_endpoint()
    results['error_handling'] = test_invalid_file()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"Tests Passed: {Colors.GREEN}{passed}{Colors.NC}")
    print(f"Tests Failed: {Colors.RED}{failed}{Colors.NC}")
    if skipped > 0:
        print(f"Tests Skipped: {Colors.YELLOW}{skipped}{Colors.NC}")
    
    print()
    
    if failed == 0 and passed > 0:
        print_success("All tests passed! Your API is working correctly! ✓")
        print_info(f"API URL: {API_URL}")
        print_info(f"API Docs: {API_URL}/docs")
        return 0
    else:
        print_error("Some tests failed. Check the logs above.")
        print_info("Common issues:")
        print("  - App not fully started yet (wait 2-3 minutes)")
        print("  - Environment variables not set correctly")
        print("  - Code deployment failed")
        print()
        print_info("Check logs with:")
        print("  az webapp log tail --name app-expense-receipt-api --resource-group rg-creditcard-expense-management")
        return 1

if __name__ == "__main__":
    sys.exit(main())