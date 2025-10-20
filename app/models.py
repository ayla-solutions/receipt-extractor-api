from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class LineItem(BaseModel):
    """Model for individual receipt line items (matches receiptlineitems table)"""
    line_number: int = Field(description="Sequential line number (1, 2, 3...)")
    line_description: str = Field(description="Item description/name")
    quantity: Optional[float] = Field(default=None, description="Quantity purchased")
    unit_price: Optional[float] = Field(default=None, description="Price per unit")
    line_amount: float = Field(description="Total price for this line item (required)")
    gst_amount: Optional[float] = Field(default=None, description="GST for this line item")
    item_category: Optional[str] = Field(default=None, description="Category (Fuel, Food, etc.)")
    notes: Optional[str] = Field(default=None, description="Additional notes")

class ReceiptExtraction(BaseModel):
    """Model for receipt extraction (matches receipts table)"""
    
    # Required fields
    merchant_name: str = Field(description="Name of the merchant/store")
    transaction_amount: float = Field(description="Total transaction amount")
    transaction_date: str = Field(description="Date of transaction in YYYY-MM-DD format")
    
    # Optional fields
    receipt_number: Optional[str] = Field(default=None, description="Receipt or invoice number")
    gst_amount: Optional[float] = Field(default=None, description="Total GST/tax amount")
    payment_method: str = Field(default="card", description="Payment method (card, cash, etc.)")
    
    # Line items (required - at least one)
    items: List[LineItem] = Field(description="List of items purchased (at least 1)")
    
    # Metadata fields
    ocr_confidence: float = Field(description="OCR confidence score 0-1")
    receipt_status: int = Field(default=2, description="Status: 2 = AI Processed")
    is_manually_entered: bool = Field(default=False, description="Always False for API")
    
    # Validation
    items_total_matches: bool = Field(description="Whether line items sum to total")
    items_total_difference: Optional[float] = Field(default=None, description="Difference if mismatch")

class ReceiptResponse(BaseModel):
    """API response model"""
    success: bool
    receipt_data: Optional[ReceiptExtraction] = None
    ocr_raw_json: Optional[dict] = None
    error: Optional[str] = None
    validation_warnings: Optional[List[str]] = Field(default=None, description="Any validation warnings")