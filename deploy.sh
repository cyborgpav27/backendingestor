#!/bin/bash

# Drug Discovery API Deployment Script
# This script automates the deployment of the complete API infrastructure

set -e  # Exit on any error

# Configuration variables
STACK_NAME="drug-discovery-api"
REGION="us-east-1"  # Change to your preferred region
ENVIRONMENT="dev"   # Change for different environments

echo "🚀 Starting deployment of Drug Discovery API..."

# Step 1: Package Lambda function code
echo "📦 Packaging Lambda function..."
zip -r lambda-deployment-package.zip lambda_function.py

# Step 2: Create S3 bucket for deployment artifacts (if it doesn't exist)
BUCKET_NAME="drug-discovery-api-deployments-$(date +%s)"
echo "🪣 Creating S3 bucket: $BUCKET_NAME"
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Step 3: Upload Lambda package to S3
echo "⬆️ Uploading Lambda package to S3..."
aws s3 cp lambda-deployment-package.zip s3://$BUCKET_NAME/

# Step 4: Update CloudFormation template with S3 location
echo "📝 Updating template with S3 location..."
python update_template.py $BUCKET_NAME

# Step 5: Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file infrastructure-deploy.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides Environment=$ENVIRONMENT \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

# Step 6: Get API endpoint URL
echo "🔗 Getting API endpoint URL..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

echo "✅ Deployment completed successfully!"
echo "🌐 API Endpoint: $API_ENDPOINT"
echo ""
echo "📋 Available endpoints:"
echo "  POST $API_ENDPOINT/upload - Upload CSV data"
echo "  GET  $API_ENDPOINT/data - Retrieve all data"
echo "  GET  $API_ENDPOINT/data/{id} - Retrieve specific drug data"
echo ""
echo "🧪 Test the API with:"
echo "curl -X POST $API_ENDPOINT/upload \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"csv_data\": \"drug_name,target,efficacy\\nAspirin,COX-1,85.5\"}'"

# Cleanup temporary files
rm -f lambda-deployment-package.zip infrastructure-deploy.yaml

echo "🎉 Deployment script completed!"
