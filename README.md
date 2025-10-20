# Credit Card Expense Receipt OCR API

AI-powered receipt extraction API using Azure Document Intelligence for automated expense tracking.

## Features

- **Automatic Receipt Processing**: Extract merchant name, amount, date, line items, and more
- **High Accuracy**: 95-99% OCR accuracy using Azure's prebuilt receipt model
- **Multi-Format Support**: JPG, PNG, PDF receipts
- **Structured Output**: JSON response matching Dataverse schema
- **Payment Method Detection**: Automatically identifies EFTPOS, card, cash
- **Line Item Extraction**: Individual items with quantities, prices, and GST
- **Validation**: Checks if line items sum to total amount
- **Production Ready**: Deployed on Azure App Service with auto-scaling

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check - API status |
| `/health` | GET | Detailed health check with Azure credentials status |
| `/extract` | POST | Extract structured data from receipt image |
| `/extract/raw` | POST | Get raw Azure Document Intelligence response |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

## Architecture
```
Receipt Image (JPG/PNG/PDF)
    ↓
FastAPI Application
    ↓
Azure Document Intelligence (prebuilt-receipt model)
    ↓
Structured JSON Response
    ↓
Dataverse / Power Apps
```

## Technology Stack

- **Framework**: FastAPI 0.109.0
- **OCR Engine**: Azure Document Intelligence (Form Recognizer)
- **Runtime**: Python 3.11
- **Deployment**: Azure App Service (Linux)
- **CI/CD**: GitHub Actions
- **Local Dev**: Docker Compose
- **API Server**: Uvicorn + Gunicorn

## Installation

### Prerequisites

- Python 3.11+
- Azure subscription with Document Intelligence resource
- Docker Desktop (for local development)
- Git

### Local Setup (Docker)

1. **Clone the repository**
```bash
git clone https://github.com/ayla-solutions/receipt-extractor-api.git
cd receipt-extractor-api
```

2. **Create `.env` file**
```bash
AZURE_DOC_INTEL_ENDPOINT=https://australiaeast.api.cognitive.microsoft.com/
AZURE_DOC_INTEL_KEY=your_key_here
```

3. **Build and run with Docker Compose**
```bash
docker-compose build
docker-compose up -d
```

4. **Test the API**
```bash
curl http://localhost:8000/health
```

API will be available at: `http://localhost:8000`

### Local Setup (Python Virtual Environment)
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Azure Deployment

### Existing Resources

- **Resource Group**: `rg-creditcard-expense-management`
- **Document Intelligence**: `doc-intel-expense-receipts`
- **App Service Plan**: `plan-expense-receipt-api`
- **Web App**: `app-expense-receipt-api`
- **Location**: Australia East

### Deployment via GitHub Actions

**Automatic deployment on push to `main` branch.**

1. Push your changes:
```bash
git add .
git commit -m "Update API"
git push origin main
```

2. GitHub Actions will automatically:
   - Build the application
   - Run tests (if configured)
   - Deploy to Azure App Service

3. Monitor deployment: https://github.com/ayla-solutions/receipt-extractor-api/actions

### Manual Deployment (ZIP)
```powershell
# Create deployment package
Compress-Archive -Path app,requirements.txt -DestinationPath deploy.zip -Force

# Deploy to Azure
az webapp deployment source config-zip `
  --resource-group rg-creditcard-expense-management `
  --name app-expense-receipt-api `
  --src deploy.zip

# Clean up
Remove-Item deploy.zip
```

## Testing

### Run Local Tests
```bash
python test_local.py
```

### Test Azure Deployment
```bash
python test_azure_api.py
```

### Manual API Testing

**Health Check:**
```bash
curl https://app-expense-receipt-api.azurewebsites.net/health
```

**Extract Receipt:**
```bash
curl -X POST "https://app-expense-receipt-api.azurewebsites.net/extract" \
  -F "file=@test_receipt.jpg"
```

**Interactive Documentation:**
Visit: https://app-expense-receipt-api.azurewebsites.net/docs

## API Response Format

### Successful Extraction
```json
{
  "success": true,
  "receipt_data": {
    "merchant_name": "T & M FRESH",
    "transaction_amount": 21.97,
    "transaction_date": "2025-10-15",
    "receipt_number": "796850",
    "gst_amount": 2.00,
    "payment_method": "card",
    "items": [
      {
        "line_number": 1,
        "line_description": "Banana Cavendish",
        "quantity": 1.305,
        "unit_price": 3.99,
        "line_amount": 5.21,
        "gst_amount": 0.47
      }
    ],
    "ocr_confidence": 0.975,
    "receipt_status": 2,
    "is_manually_entered": false,
    "items_total_matches": true,
    "items_total_difference": 0.0
  },
  "ocr_raw_json": { ... },
  "validation_warnings": null
}
```

### Error Response
```json
{
  "success": false,
  "receipt_data": null,
  "error": "Unsupported file type: text/plain",
  "validation_warnings": null
}
```

## Project Structure
```
receipt-extractor-api/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   └── utils.py             # Azure Document Intelligence integration
├── .github/
│   └── workflows/
│       └── main_app-expense-receipt-api.yml  # GitHub Actions workflow
├── .gitignore               # Git ignore rules
├── .dockerignore            # Docker ignore rules
├── Dockerfile               # Docker container definition
├── docker-compose.yml       # Local development stack
├── requirements.txt         # Python dependencies
├── test_local.py           # Local testing script
├── test_azure_api.py       # Azure deployment testing script
└── README.md               # This file
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_DOC_INTEL_ENDPOINT` | Azure Document Intelligence endpoint URL | Yes |
| `AZURE_DOC_INTEL_KEY` | Azure API key | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, WARNING) | No (default: INFO) |

### Azure App Service Settings

Set in Azure Portal → App Service → Configuration → Application Settings:
- `AZURE_DOC_INTEL_ENDPOINT`
- `AZURE_DOC_INTEL_KEY`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- `WEBSITE_HTTPLOGGING_RETENTION_DAYS=7`

## Performance

- **Processing Time**: 1-3 seconds per receipt
- **Accuracy**: 95-99% on clear receipts
- **Supported Formats**: JPG, PNG, PDF
- **Max File Size**: 50MB (Azure limit)
- **Concurrent Requests**: Auto-scaling based on load

## Cost Estimation

| Service | SKU | Monthly Cost |
|---------|-----|--------------|
| Document Intelligence | F0 (Free) | $0 (1st 500 pages free) |
| Document Intelligence | S0 (Paid) | ~$1 per 1,000 pages |
| App Service Plan | B1 (Basic) | ~$13/month |
| **Total** | | **~$13-14/month** |

## Security

- Environment variables for secrets (not in code)
- HTTPS only in production
- Azure managed identities (recommended for production)
- No temporary files stored on disk
- Automatic cleanup after processing
- API authentication not implemented (add for production)

### Recommended Production Security

1. Enable Azure AD authentication
2. Use Azure Key Vault for secrets
3. Enable Application Insights for monitoring
4. Configure CORS policies
5. Add rate limiting

## 🐛 Troubleshooting

### API Returns 500 Error

**Check logs:**
```bash
az webapp log tail --name app-expense-receipt-api --resource-group rg-creditcard-expense-management
```

**Common causes:**
- Environment variables not set
- Invalid Azure credentials
- Python dependencies missing

### Low Confidence Scores

**Solutions:**
- Ensure receipt image is clear and well-lit
- Use higher resolution images
- Avoid blurry or damaged receipts

### "No receipt detected"

**Solutions:**
- Check file format (JPG, PNG, PDF only)
- Ensure image contains visible text
- Try scanning instead of photographing

## Documentation

- **API Docs (Interactive)**: https://app-expense-receipt-api.azurewebsites.net/docs
- **Azure Document Intelligence**: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software owned by AYLA Solutions.

## Authors

- **AYLA Solutions** - Credit Card Expense Management Team
- **Contact**: support@aylasolutions.com.au

## Related Projects

- Credit Card Expense Management Power App
- Dataverse Integration
- Power Automate Flows

## Support

For issues, questions, or feature requests:
- Create an issue on GitHub
- Email: support@aylasolutions.com.au
- Documentation: Internal AYLA Wiki

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Status**: Production Ready