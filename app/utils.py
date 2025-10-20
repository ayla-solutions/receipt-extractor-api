"""
Azure Document Intelligence implementation for receipt extraction
Purpose-built for receipts with high accuracy
"""

import logging
import os
from typing import Dict, Any
from datetime import datetime
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
AZURE_DOC_INTEL_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT")
AZURE_DOC_INTEL_KEY = os.getenv("AZURE_DOC_INTEL_KEY")


def _extract_amount(field) -> float:
    """
    Helper to extract amount from Azure field (handles different return types)
    Azure sometimes returns value.amount, sometimes just value as float
    """
    if not field or not field.value:
        return None
    
    # Check if value has amount attribute (CurrencyValue object)
    if hasattr(field.value, 'amount'):
        return float(field.value.amount)
    
    # Otherwise it's already a float
    return float(field.value)


def _map_payment_method(payment_method: str) -> str:
    """
    Map various payment method strings to standardized values
    EFTPOS -> card (as per requirement)
    """
    if not payment_method:
        return "card"  # Default to card
    
    payment_lower = payment_method.lower().strip()
    
    # EFTPOS mapping
    if "eftpos" in payment_lower:
        return "card"
    
    # Card variations
    if any(keyword in payment_lower for keyword in ["card", "credit", "debit", "visa", "mastercard", "amex"]):
        return "card"
    
    # Cash
    if "cash" in payment_lower:
        return "cash"
    
    # Default to card
    return "card"


def _extract_receipt_number(fields: dict, raw_text: str = None) -> str:
    """
    Try multiple strategies to extract receipt number
    """
    # Strategy 1: Direct receipt number field
    if fields.get("ReceiptNumber"):
        return str(fields.get("ReceiptNumber").value)
    
    # Strategy 2: Transaction ID
    if fields.get("TransactionId"):
        return str(fields.get("TransactionId").value)
    
    # Strategy 3: Invoice number
    if fields.get("InvoiceNumber"):
        return str(fields.get("InvoiceNumber").value)
    
    # Strategy 4: Look in raw OCR text for patterns like #796850
    if raw_text:
        import re
        # Pattern: # followed by 5-10 digits
        match = re.search(r'#(\d{5,10})', raw_text)
        if match:
            return match.group(1)
        
        # Pattern: Receipt: 12345 or Receipt No: 12345
        match = re.search(r'(?:receipt|rcpt|trans|txn)[\s:#-]*(\d{5,10})', raw_text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_receipt_azure_doc_intelligence(file_path: str) -> Dict[str, Any]:
    """
    Extract receipt data using Azure Document Intelligence
    
    Args:
        file_path: Path to the receipt image/PDF
        
    Returns:
        Dictionary with success status and extracted data
    """
    try:
        # Validate credentials
        if not AZURE_DOC_INTEL_ENDPOINT or not AZURE_DOC_INTEL_KEY:
            raise ValueError("Azure Document Intelligence credentials not configured")
        
        # Initialize client
        client = DocumentAnalysisClient(
            endpoint=AZURE_DOC_INTEL_ENDPOINT,
            credential=AzureKeyCredential(AZURE_DOC_INTEL_KEY)
        )
        
        logger.info(f"Analyzing receipt with Azure Document Intelligence: {file_path}")
        
        # Analyze receipt
        with open(file_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
            result = poller.result()
        
        # Extract raw text for receipt number detection
        raw_text = ""
        if result.content:
            raw_text = result.content
        
        # Process results
        if not result.documents:
            return {
                "success": False,
                "error": "No receipt detected in image"
            }
        
        receipt = result.documents[0]
        fields = receipt.fields
        
        # Extract fields with confidence scores
        merchant_name = fields.get("MerchantName")
        total = fields.get("Total")
        transaction_date = fields.get("TransactionDate")
        transaction_time = fields.get("TransactionTime")
        
        # Get items for receipt number (often in item descriptions)
        items = fields.get("Items")
        
        # Extract receipt number using multiple strategies
        receipt_number = _extract_receipt_number(fields, raw_text)
        
        # Get tax/GST
        tax = fields.get("TotalTax") or fields.get("Tax")
        
        # Get and map payment method
        payment_method_raw = None
        if fields.get("PaymentMethod"):
            payment_method_raw = fields.get("PaymentMethod").value
        payment_method = _map_payment_method(payment_method_raw)
        
        # Extract line items with proper structure
        items_list = []
        items_field = fields.get("Items")
        line_number = 1
        
        if items_field and items_field.value:
            for item in items_field.value:
                try:
                    item_fields = item.value if hasattr(item, 'value') else item
                    
                    # Extract item details
                    description = None
                    quantity = None
                    unit_price = None
                    line_amount = None
                    gst_amount = None
                    
                    if hasattr(item_fields, 'get'):
                        desc_field = item_fields.get("Description")
                        qty_field = item_fields.get("Quantity")
                        price_field = item_fields.get("Price")
                        total_field = item_fields.get("TotalPrice")
                        tax_field = item_fields.get("Tax")
                        
                        description = desc_field.value if desc_field else None
                        quantity = float(qty_field.value) if qty_field and qty_field.value else None
                        unit_price = _extract_amount(price_field)
                        line_amount = _extract_amount(total_field)
                        gst_amount = _extract_amount(tax_field)
                    
                    # Only add if we have at least description or line_amount
                    if description or line_amount:
                        items_list.append({
                            "line_number": line_number,
                            "line_description": description or "Item",
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "line_amount": line_amount if line_amount else 0.0,
                            "gst_amount": gst_amount,
                            "item_category": None,  # Can be enhanced later
                            "notes": None
                        })
                        line_number += 1
                except Exception as e:
                    logger.warning(f"Error extracting item: {e}")
                    continue
        
        # CRITICAL: If no line items found, create ONE line item with total
        # (As per requirement: "Every receipt MUST have at least 1 line item")
        if not items_list:
            merchant_value = merchant_name.value if merchant_name else "Unknown Item"
            total_value = _extract_amount(total) if total else 0.0
            
            items_list.append({
                "line_number": 1,
                "line_description": merchant_value,
                "quantity": 1,
                "unit_price": total_value,
                "line_amount": total_value,
                "gst_amount": _extract_amount(tax),
                "item_category": None,
                "notes": "Auto-generated: No line items detected"
            })
        
        # Validate: Line items should sum to total
        items_total = sum(item["line_amount"] for item in items_list if item.get("line_amount"))
        transaction_total = _extract_amount(total) if total else 0.0
        items_match = abs(items_total - transaction_total) < 0.05  # Allow 5 cent rounding
        items_difference = round(transaction_total - items_total, 2) if not items_match else 0.0
        
        logger.info(f"Extracted {len(items_list)} line items. Total: ${items_total:.2f}, Expected: ${transaction_total:.2f}, Match: {items_match}")
        
        # Format date to YYYY-MM-DD
        formatted_date = None
        if transaction_date and transaction_date.value:
            try:
                if isinstance(transaction_date.value, datetime):
                    formatted_date = transaction_date.value.strftime("%Y-%m-%d")
                else:
                    formatted_date = str(transaction_date.value)
            except Exception as e:
                logger.warning(f"Date formatting error: {e}")
                formatted_date = str(transaction_date.value) if transaction_date.value else None
        
        # Calculate average confidence
        confidences = []
        if merchant_name and merchant_name.confidence:
            confidences.append(merchant_name.confidence)
        if total and total.confidence:
            confidences.append(total.confidence)
        if transaction_date and transaction_date.confidence:
            confidences.append(transaction_date.confidence)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Build response matching Dataverse schema
        receipt_data = {
            # Required fields
            "merchant_name": merchant_name.value if merchant_name else "Unknown Merchant",
            "transaction_amount": transaction_total,
            "transaction_date": formatted_date,
            
            # Optional fields
            "receipt_number": receipt_number,
            "gst_amount": _extract_amount(tax),
            "payment_method": payment_method,  # Mapped value (eftpos -> card)
            
            # Line items (at least 1 required)
            "items": items_list,
            
            # Metadata
            "ocr_confidence": avg_confidence,
            "receipt_status": 2,  # AI Processed
            "is_manually_entered": False,
            
            # Validation
            "items_total_matches": items_match,
            "items_total_difference": items_difference if not items_match else None
        }
        
        # Prepare raw data for debugging
        raw_data = {
            "merchant_name": {
                "value": merchant_name.value if merchant_name else None,
                "confidence": merchant_name.confidence if merchant_name else None
            },
            "total": {
                "value": transaction_total,
                "confidence": total.confidence if total else None
            },
            "transaction_date": {
                "value": str(transaction_date.value) if transaction_date and transaction_date.value else None,
                "confidence": transaction_date.confidence if transaction_date else None
            },
            "tax": {
                "value": _extract_amount(tax),
                "confidence": tax.confidence if tax else None
            },
            "payment_method_raw": payment_method_raw,
            "payment_method_mapped": payment_method,
            "receipt_number_source": "Extracted from OCR" if receipt_number else "Not found",
            "items_count": len(items_list),
            "items_total": items_total,
            "items_match_total": items_match,
            "all_fields": [field for field in fields.keys()]
        }
        
        # Generate validation warnings
        warnings = []
        if not items_match:
            warnings.append(f"Line items total (${items_total:.2f}) does not match transaction amount (${transaction_total:.2f})")
        if avg_confidence < 0.8:
            warnings.append(f"Low OCR confidence: {avg_confidence*100:.1f}%")
        if not receipt_number:
            warnings.append("Receipt number not found")
        if len(items_list) == 1 and items_list[0].get("notes") == "Auto-generated: No line items detected":
            warnings.append("No line items detected - created default item")
        
        logger.info(f"Successfully extracted: {receipt_data.get('merchant_name')}, Total: ${receipt_data.get('transaction_amount')}, Items: {len(items_list)}, Warnings: {len(warnings)}")
        
        return {
            "success": True,
            "receipt_data": receipt_data,
            "raw_data": raw_data,
            "validation_warnings": warnings if warnings else None
        }
        
    except Exception as e:
        logger.error(f"Azure Document Intelligence extraction failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }