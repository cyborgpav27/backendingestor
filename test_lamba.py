import unittest
import json
from unittest.mock import patch, MagicMock
from lambda_function import (
    lambda_handler, validate_csv_data, store_drug_data, 
    apply_filters, create_response
)

class TestDrugDiscoveryAPI(unittest.TestCase):
    """
    Comprehensive test suite for the drug discovery API
    """
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.valid_csv_data = """drug_name,target,efficacy,compound_id,mechanism,phase,indication
Aspirin,COX-1,85.5,ASP001,COX inhibition,Phase III,Pain relief
Ibuprofen,COX-2,78.2,IBU001,COX inhibition,Phase III,Inflammation
Paracetamol,COX-3,92.1,PAR001,COX inhibition,Phase III,Fever reduction"""
        
        self.invalid_csv_data = """drug_name,target
Aspirin,COX-1
Ibuprofen"""  # Missing efficacy column
    
    def test_csv_validation_success(self):
        """Test successful CSV validation with valid data"""
        result = validate_csv_data(self.valid_csv_data)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['data']), 3)
        self.assertEqual(result['data'][0]['drug_name'], 'Aspirin')
        self.assertEqual(result['data'][0]['efficacy'], 85.5)
    
    def test_csv_validation_missing_required_fields(self):
        """Test CSV validation failure when required fields are missing"""
        result = validate_csv_data(self.invalid_csv_data)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('Missing required fields', result['errors'][0])
    
    def test_csv_validation_invalid_efficacy(self):
        """Test CSV validation with invalid efficacy values"""
        invalid_efficacy_csv = """drug_name,target,efficacy
Aspirin,COX-1,invalid_number
Ibuprofen,COX-2,150"""  # Over 100
        
        result = validate_csv_data(invalid_efficacy_csv)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(any('efficacy must be a valid number' in error for error in result['errors']))
        self.assertTrue(any('efficacy must be between 0 and 100' in error for error in result['errors']))
    
    def test_csv_validation_empty_required_fields(self):
        """Test CSV validation with empty required fields"""
        empty_fields_csv = """drug_name,target,efficacy
,COX-1,85.5
Ibuprofen,,78.2"""
        
        result = validate_csv_data(empty_fields_csv)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(any('drug_name is required but empty' in error for error in result['errors']))
        self.assertTrue(any('target is required but empty' in error for error in result['errors']))
    
    @patch('lambda_function.table')
    def test_store_drug_data_success(self, mock_table):
        """Test successful storage of drug data in DynamoDB"""
        # Mock DynamoDB batch writer
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_batch
        
        test_data = [
            {'drug_name': 'Aspirin', 'target': 'COX-1', 'efficacy': 85.5}
        ]
        
        result = store_drug_data(test_data)
        
        self.assertEqual(len(result), 1)
        mock_batch.put_item.assert_called_once()
    
    def test_apply_filters_drug_name(self):
        """Test filtering by drug name"""
        test_items = [
            {'drug_name': 'Aspirin', 'target': 'COX-1', 'efficacy': 85.5},
            {'drug_name': 'Ibuprofen', 'target': 'COX-2', 'efficacy': 78.2}
        ]
        
        filters = {'drug_name': 'asp'}
        result = apply_filters(test_items, filters)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['drug_name'], 'Aspirin')
    
    def test_apply_filters_min_efficacy(self):
        """Test filtering by minimum efficacy"""
        test_items = [
            {'drug_name': 'Aspirin', 'target': 'COX-1', 'efficacy': 85.5},
            {'drug_name': 'Ibuprofen', 'target': 'COX-2', 'efficacy': 78.2}
        ]
        
        filters = {'min_efficacy': '80'}
        result = apply_filters(test_items, filters)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['drug_name'], 'Aspirin')
    
    def test_create_response_format(self):
        """Test API response format"""
        response = create_response(200, {'message': 'success'})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Content-Type', response['headers'])
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'success')
    
    @patch('lambda_function.handle_csv_upload')
    def test_lambda_handler_post_upload(self, mock_upload):
        """Test Lambda handler routing for POST /upload"""
        mock_upload.return_value = create_response(200, {'message': 'success'})
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload',
            'body': json.dumps({'csv_data': self.valid_csv_data})
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 200)
        mock_upload.assert_called_once_with(event)
    
    @patch('lambda_function.handle_data_retrieval')
    def test_lambda_handler_get_data(self, mock_retrieval):
        """Test Lambda handler routing for GET /data"""
        mock_retrieval.return_value = create_response(200, {'data': []})
        
        event = {
            'httpMethod': 'GET',
            'path': '/data'
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 200)
        mock_retrieval.assert_called_once_with(event)
    
    def test_lambda_handler_invalid_endpoint(self):
        """Test Lambda handler with invalid endpoint"""
        event = {
            'httpMethod': 'GET',
            'path': '/invalid'
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 404)

if __name__ == '__main__':
    # Run the test suite
    unittest.main()
