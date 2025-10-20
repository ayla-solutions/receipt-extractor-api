from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import logging
from app.models import ReceiptResponse, ReceiptExtraction
from app.utils import extract_receipt_azure_doc_intelligence, AZURE_DOC_INTEL_ENDPOINT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Credit Card Expense Receipt OCR API",
    description="AI-powered receipt extraction for credit card expense management",
    version="1.0.0"
)

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Credit Card Expense Receipt OCR API",
        "version": "1.0.0",
        "provider": "Azure Document Intelligence"
    }

@app.get("/health")
def health_check():
    """Detailed health check"""
    try:
        # Check if Azure credentials are set
        endpoint = AZURE_DOC_INTEL_ENDPOINT
        key = os.getenv("AZURE_DOC_INTEL_KEY")
        
        if not endpoint or not key:
            return {
                "status": "degraded",
                "azure_doc_intelligence": False,
                "error": "Azure credentials not configured"
            }
        
        return {
            "status": "healthy",
            "azure_doc_intelligence": True,
            "endpoint": endpoint
        }
    except Exception as e:
        return {
            "status": "degraded",
            "azure_doc_intelligence": False,
            "error": str(e)
        }

@app.post("/extract", response_model=ReceiptResponse)
async def extract_receipt(file: UploadFile = File(...)):
    """
    Extract structured data from a receipt image using Azure Document Intelligence
    
    Args:
        file: Receipt image file (JPG, PNG, PDF)
        
    Returns:
        JSON with extracted receipt fields matching database schema
    """
    temp_path = None
    
    try:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        logger.info(f"Processing receipt: {file.filename}")
        
        # Extract using Azure Document Intelligence
        result = extract_receipt_azure_doc_intelligence(temp_path)
        
        if result["success"]:
            receipt_data = ReceiptExtraction(**result["receipt_data"])
            
            return ReceiptResponse(
                success=True,
                receipt_data=receipt_data,
                ocr_raw_json=result.get("raw_data")
            )
        else:
            return ReceiptResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
        
    except Exception as e:
        logger.error(f"Error processing receipt: {str(e)}", exc_info=True)
        return ReceiptResponse(
            success=False,
            error=f"Processing failed: {str(e)}"
        )
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

@app.post("/extract/raw")
async def extract_raw_text(file: UploadFile = File(...)):
    """
    Get raw Azure Document Intelligence response
    Useful for debugging and testing
    """
    temp_path = None
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        result = extract_receipt_azure_doc_intelligence(temp_path)
        
        return {
            "success": result["success"],
            "raw_azure_response": result.get("raw_data"),
            "error": result.get("error")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
        
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)