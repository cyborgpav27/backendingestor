# Drug Discovery API - Backend Ingestor

A serverless REST API for ingesting and managing drug discovery data using AWS Lambda, API Gateway, and DynamoDB.

## Architecture

```
Client → API Gateway → Lambda Function → DynamoDB
```

### Components

- **API Gateway**: REST API endpoints for data ingestion and retrieval
- **Lambda Function**: Python-based serverless function for processing requests
- **DynamoDB**: NoSQL database for storing drug discovery data
- **S3**: Storage for Lambda deployment packages

## Flow

1. **CSV Upload**: Client sends CSV data via POST request to `/upload` endpoint
2. **Validation**: Lambda validates CSV format and required fields (drug_name, target, efficacy)
3. **Storage**: Validated data is stored in DynamoDB with unique IDs
4. **Retrieval**: Clients can query data via GET endpoints

## Prerequisites

- AWS CLI configured with credentials
- Python 3.9+
- Bash shell (Git Bash on Windows)

## Deployment

```bash
./deploy.sh
```

The script will:
1. Package the Lambda function
2. Create an S3 bucket for deployment artifacts
3. Deploy CloudFormation stack with all resources
4. Output the API endpoint URL

## API Endpoints

### 1. Upload CSV Data
**POST** `/upload`

Upload drug discovery data in CSV format.

**Request Body:**
```json
{
  "csv_data": "drug_name,target,efficacy\nAspirin,COX-1,85.5\nIbuprofen,COX-2,78.3"
}
```

**Response:**
```json
{
  "message": "CSV data uploaded successfully",
  "records_stored": 2,
  "validation_summary": {
    "total_rows": 2,
    "valid_rows": 2
  }
}
```

### 2. Get All Data
**GET** `/data`

Retrieve all drug records with optional filtering.

**Query Parameters:**
- `drug_name`: Filter by drug name (partial match)
- `target`: Filter by target (partial match)
- `min_efficacy`: Filter by minimum efficacy value

**Response:**
```json
{
  "total_records": 2,
  "data": [
    {
      "drug_id": "uuid",
      "drug_name": "Aspirin",
      "target": "COX-1",
      "efficacy": 85.5,
      "created_at": "2026-02-28T18:00:00",
      "updated_at": "2026-02-28T18:00:00"
    }
  ]
}
```

### 3. Get Single Drug
**GET** `/data/{drug_id}`

Retrieve a specific drug record by ID.

**Response:**
```json
{
  "drug_id": "uuid",
  "drug_name": "Aspirin",
  "target": "COX-1",
  "efficacy": 85.5,
  "created_at": "2026-02-28T18:00:00",
  "updated_at": "2026-02-28T18:00:00"
}
```

## Sample Test Cases

### Test 1: Upload Single Drug (JSON Format)
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: application/json' \
  -d '{"csv_data": "drug_name,target,efficacy\nAspirin,COX-1,85.5"}'
```

**Expected Response:**
```json
{
  "message": "CSV data uploaded successfully",
  "records_stored": 1,
  "validation_summary": {
    "total_rows": 1,
    "valid_rows": 1
  }
}
```

### Test 2: Upload CSV File Directly

**Step 1:** Create a CSV file named `sample_drugs.csv` with the following content:
```csv
drug_name,target,efficacy
Aspirin,COX-1,85.5
Ibuprofen,COX-2,78.3
Naproxen,COX-1/COX-2,82.1
```

**Step 2:** Save the file in your current directory

**Step 3:** Run the following curl command:
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: text/csv' \
  --data-binary @sample_drugs.csv
```

**Note:** Make sure you're in the same directory as the CSV file, or provide the full path:
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: text/csv' \
  --data-binary @/path/to/sample_drugs.csv
```

**Expected Response:**
```json
{
  "message": "CSV data uploaded successfully",
  "records_stored": 3,
  "validation_summary": {
    "total_rows": 3,
    "valid_rows": 3
  }
}
```

### Test 3: Upload Multiple Drugs (JSON Format)
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: application/json' \
  -d '{"csv_data": "drug_name,target,efficacy\nAspirin,COX-1,85.5\nIbuprofen,COX-2,78.3\nNaproxen,COX-1/COX-2,82.1"}'
```

### Test 4: Retrieve All Data
```bash
curl -X GET https://YOUR_API_ENDPOINT/dev/data
```

### Test 5: Filter by Drug Name
```bash
curl -X GET "https://YOUR_API_ENDPOINT/dev/data?drug_name=Aspirin"
```

### Test 6: Filter by Minimum Efficacy
```bash
curl -X GET "https://YOUR_API_ENDPOINT/dev/data?min_efficacy=80"
```

### Test 7: Invalid CSV (Missing Required Field)
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: application/json' \
  -d '{"csv_data": "drug_name,target\nAspirin,COX-1"}'
```

**Expected Response:**
```json
{
  "error": "CSV validation failed",
  "details": ["Missing required fields: ['efficacy']"]
}
```

### Test 8: Invalid Efficacy Value
```bash
curl -X POST https://YOUR_API_ENDPOINT/dev/upload \
  -H 'Content-Type: application/json' \
  -d '{"csv_data": "drug_name,target,efficacy\nAspirin,COX-1,150"}'
```

**Expected Response:**
```json
{
  "error": "CSV validation failed",
  "details": ["Row 2: efficacy must be between 0 and 100"]
}
```

## CSV Format

### Required Fields
- `drug_name`: Name of the drug (max 100 characters)
- `target`: Biological target
- `efficacy`: Efficacy value (0-100)

### Optional Fields
- `compound_id`: Compound identifier
- `mechanism`: Mechanism of action
- `phase`: Clinical trial phase
- `indication`: Medical indication

## Data Validation Rules

1. All required fields must be present
2. Efficacy must be a number between 0 and 100
3. Drug name cannot exceed 100 characters
4. Empty required fields are rejected

## Error Handling

- **400**: Invalid request (malformed JSON, validation errors)
- **404**: Resource not found
- **500**: Internal server error

## Cleanup

To delete all resources:
```bash
aws cloudformation delete-stack --stack-name drug-discovery-api --region us-east-1
```

## Project Structure

```
backendingestor/
├── lambda_function.py          # Lambda handler and business logic
├── infrastructure.yaml         # CloudFormation template
├── deploy.sh                   # Deployment script
├── update_template.py          # Template transformation utility
└── README.md                   # This file
```

## Notes

- DynamoDB uses on-demand billing mode
- Point-in-time recovery is enabled for data protection
- CORS is enabled for web application integration
- Lambda timeout is set to 30 seconds
- Lambda memory is allocated 256 MB
