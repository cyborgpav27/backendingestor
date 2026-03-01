import json
import boto3
import csv
import io
import base64
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

# Configure logging for better debugging and monitoring
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS services clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('drug-discovery-data')  # DynamoDB table name

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function that processes API Gateway requests
    
    Args:
        event: API Gateway event containing request details
        context: Lambda context object
        
    Returns:
        Dict containing HTTP response with status code, headers, and body
    """
    try:
        # Extract HTTP method and path from the API Gateway event
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        # Log incoming request for debugging purposes
        logger.info(f"Processing {http_method} request to {path}")
        
        # Route requests based on HTTP method and path
        if http_method == 'POST' and path == '/upload':
            return handle_csv_upload(event)
        elif http_method == 'GET' and path == '/data':
            return handle_data_retrieval(event)
        elif http_method == 'GET' and path.startswith('/data/'):
            # Extract drug ID from path for individual drug retrieval
            drug_id = path.split('/')[-1]
            return handle_single_drug_retrieval(drug_id)
        else:
            # Return 404 for unsupported endpoints
            return create_response(404, {'error': 'Endpoint not found'})
            
    except Exception as e:
        # Log error and return 500 status for unexpected errors
        logger.error(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def handle_csv_upload(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle CSV file upload and validation
    
    Args:
        event: API Gateway event containing the CSV file data
        
    Returns:
        Dict containing response with upload status and validation results
    """
    try:
        # Parse request body (could be base64 encoded for binary data)
        body = event.get('body', '')
        is_base64_encoded = event.get('isBase64Encoded', False)
        
        # Decode base64 if necessary (for file uploads through API Gateway)
        if is_base64_encoded:
            body = base64.b64decode(body).decode('utf-8')
        
        # Parse JSON body to extract CSV content
        request_data = json.loads(body) if body else {}
        csv_content = request_data.get('csv_data', '')
        
        if not csv_content:
            return create_response(400, {'error': 'No CSV data provided'})
        
        # Validate and parse CSV data
        validation_result = validate_csv_data(csv_content)
        
        if not validation_result['is_valid']:
            return create_response(400, {
                'error': 'CSV validation failed',
                'details': validation_result['errors']
            })
        
        # Store validated data in DynamoDB
        stored_records = store_drug_data(validation_result['data'])
        
        # Return success response with stored record count
        return create_response(200, {
            'message': 'CSV data uploaded successfully',
            'records_stored': len(stored_records),
            'validation_summary': {
                'total_rows': len(validation_result['data']),
                'valid_rows': len(stored_records)
            }
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON format'})
    except Exception as e:
        logger.error(f"Error in CSV upload: {str(e)}")
        return create_response(500, {'error': 'Failed to process CSV upload'})

def validate_csv_data(csv_content: str) -> Dict[str, Any]:
    """
    Validate CSV data format and required fields
    
    Args:
        csv_content: String containing CSV data
        
    Returns:
        Dict containing validation results and parsed data
    """
    # Define required fields for drug discovery data
    required_fields = ['drug_name', 'target', 'efficacy']
    optional_fields = ['compound_id', 'mechanism', 'phase', 'indication']
    
    validation_result = {
        'is_valid': True,
        'errors': [],
        'data': []
    }
    
    try:
        # Parse CSV content using StringIO to simulate file reading
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Get fieldnames from CSV header
        fieldnames = csv_reader.fieldnames
        
        if not fieldnames:
            validation_result['is_valid'] = False
            validation_result['errors'].append('CSV file appears to be empty or has no header')
            return validation_result
        
        # Check if all required fields are present in CSV header
        missing_fields = [field for field in required_fields if field not in fieldnames]
        if missing_fields:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Missing required fields: {missing_fields}')
            return validation_result
        
        # Validate each row of data
        row_number = 1
        for row in csv_reader:
            row_number += 1
            row_errors = []
            
            # Check required fields are not empty
            for field in required_fields:
                if not row.get(field, '').strip():
                    row_errors.append(f'Row {row_number}: {field} is required but empty')
            
            # Validate efficacy is a number between 0 and 100
            try:
                efficacy = float(row.get('efficacy', 0))
                if not 0 <= efficacy <= 100:
                    row_errors.append(f'Row {row_number}: efficacy must be between 0 and 100')
                row['efficacy'] = Decimal(str(efficacy))
            except ValueError:
                row_errors.append(f'Row {row_number}: efficacy must be a valid number')
            
            # Validate drug_name length (reasonable limit)
            drug_name = row.get('drug_name', '').strip()
            if len(drug_name) > 100:
                row_errors.append(f'Row {row_number}: drug_name too long (max 100 characters)')
            
            # If row has errors, add to validation errors
            if row_errors:
                validation_result['errors'].extend(row_errors)
                validation_result['is_valid'] = False
            else:
                # Clean and prepare data for storage
                clean_row = {
                    'drug_name': drug_name,
                    'target': row.get('target', '').strip(),
                    'efficacy': row['efficacy'],
                    'compound_id': row.get('compound_id', '').strip(),
                    'mechanism': row.get('mechanism', '').strip(),
                    'phase': row.get('phase', '').strip(),
                    'indication': row.get('indication', '').strip()
                }
                validation_result['data'].append(clean_row)
        
        # Check if we have at least one valid row
        if not validation_result['data'] and validation_result['is_valid']:
            validation_result['is_valid'] = False
            validation_result['errors'].append('No valid data rows found in CSV')
            
    except Exception as e:
        validation_result['is_valid'] = False
        validation_result['errors'].append(f'Error parsing CSV: {str(e)}')
    
    return validation_result

def store_drug_data(drug_records: List[Dict[str, Any]]) -> List[str]:
    """
    Store validated drug data in DynamoDB
    
    Args:
        drug_records: List of validated drug data dictionaries
        
    Returns:
        List of stored record IDs
    """
    stored_ids = []
    
    try:
        # Use batch writing for better performance with multiple records
        with table.batch_writer() as batch:
            for record in drug_records:
                # Generate unique ID for each drug record
                drug_id = str(uuid.uuid4())
                
                # Prepare item for DynamoDB storage
                item = {
                    'drug_id': drug_id,
                    'drug_name': record['drug_name'],
                    'target': record['target'],
                    'efficacy': record['efficacy'],
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                # Add optional fields if they exist and are not empty
                for field in ['compound_id', 'mechanism', 'phase', 'indication']:
                    if record.get(field):
                        item[field] = record[field]
                
                # Write item to DynamoDB
                batch.put_item(Item=item)
                stored_ids.append(drug_id)
                
        logger.info(f"Successfully stored {len(stored_ids)} drug records")
        
    except Exception as e:
        logger.error(f"Error storing drug data: {str(e)}")
        raise
    
    return stored_ids

def handle_data_retrieval(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle retrieval of all drug data with optional filtering
    
    Args:
        event: API Gateway event containing query parameters
        
    Returns:
        Dict containing all drug records in JSON format
    """
    try:
        # Extract query parameters for filtering (if any)
        query_params = event.get('queryStringParameters') or {}
        
        # Scan DynamoDB table to get all records
        response = table.scan()
        items = response.get('Items', [])
        
        # Apply filters if query parameters are provided
        if query_params:
            items = apply_filters(items, query_params)
        
        # Sort by creation date (newest first)
        items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return create_response(200, {
            'total_records': len(items),
            'data': items
        })
        
    except Exception as e:
        logger.error(f"Error retrieving drug data: {str(e)}")
        return create_response(500, {'error': 'Failed to retrieve data'})

def handle_single_drug_retrieval(drug_id: str) -> Dict[str, Any]:
    """
    Handle retrieval of a single drug record by ID
    
    Args:
        drug_id: Unique identifier for the drug record
        
    Returns:
        Dict containing the specific drug record or error message
    """
    try:
        # Get specific item from DynamoDB using drug_id
        response = table.get_item(Key={'drug_id': drug_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Drug record not found'})
        
        return create_response(200, response['Item'])
        
    except Exception as e:
        logger.error(f"Error retrieving drug {drug_id}: {str(e)}")
        return create_response(500, {'error': 'Failed to retrieve drug data'})

def apply_filters(items: List[Dict[str, Any]], filters: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Apply query parameter filters to drug data
    
    Args:
        items: List of drug records
        filters: Dictionary of filter parameters
        
    Returns:
        Filtered list of drug records
    """
    filtered_items = items
    
    # Filter by drug name (case-insensitive partial match)
    if 'drug_name' in filters:
        drug_name_filter = filters['drug_name'].lower()
        filtered_items = [
            item for item in filtered_items 
            if drug_name_filter in item.get('drug_name', '').lower()
        ]
    
    # Filter by target (case-insensitive partial match)
    if 'target' in filters:
        target_filter = filters['target'].lower()
        filtered_items = [
            item for item in filtered_items 
            if target_filter in item.get('target', '').lower()
        ]
    
    # Filter by minimum efficacy
    if 'min_efficacy' in filters:
        try:
            min_efficacy = float(filters['min_efficacy'])
            filtered_items = [
                item for item in filtered_items 
                if item.get('efficacy', 0) >= min_efficacy
            ]
        except ValueError:
            logger.warning(f"Invalid min_efficacy filter: {filters['min_efficacy']}")
    
    return filtered_items

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API Gateway response
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        
    Returns:
        Formatted API Gateway response dictionary
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Enable CORS for web applications
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body, default=str)  # default=str handles datetime serialization
    }
