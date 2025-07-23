markdown# Deployment Guide

Complete deployment instructions for the Orcutt Schools Chatbot.

## Prerequisites

### Required Tools
- **AWS CLI** (configured with appropriate permissions)
- **Node.js** 18+ and npm
- **Amplify CLI** (`npm install -g @aws-amplify/cli`)
- **Python 3.9+** (for Lambda functions)

### AWS Permissions Required
- **Amplify** - Full access
- **Lambda** - Create and manage functions
- **API Gateway** - Create and configure APIs
- **DynamoDB** - Create tables and read/write access
- **Bedrock** - Model access and runtime permissions
- **S3** - Bucket creation and file access
- **CloudFront** - Distribution management
- **Route 53** - DNS management (if using custom domain)
- **Certificate Manager** - SSL certificate creation

## Backend Infrastructure Setup

### 1. Knowledge Base Setup
```bash
# 1. Create S3 bucket for documents
aws s3 mb s3://orcutt-schools-knowledge-base-docs --region us-west-2

# 2. Upload school documents
aws s3 sync ./school-documents/ s3://orcutt-schools-knowledge-base-docs/

# 3. Create Knowledge Base via AWS Console
# - Go to Amazon Bedrock Console
# - Create Knowledge Base
# - Connect to S3 bucket
# - Configure embeddings model (Titan Embeddings G1 - Text)
# - Note the Knowledge Base ID
2. DynamoDB Table Creation
bash# Create conversations table
aws dynamodb create-table \
    --table-name orcutt-chat-conversations \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-west-2
3. Lambda Function Deployment
Create Lambda Package
bash# Create deployment package
mkdir lambda-deployment
cd lambda-deployment

# Copy your Lambda code
cp ../lambda/lambda_function.py .

# Install dependencies
pip install boto3 numpy -t .

# Create deployment package
zip -r orcutt-chat-handler.zip .
Deploy Lambda Function
bash# Create Lambda function
aws lambda create-function \
    --function-name orcutt-chat-handler \
    --runtime python3.9 \
    --role arn:aws:iam::ACCOUNT-ID:role/lambda-execution-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://orcutt-chat-handler.zip \
    --timeout 300 \
    --memory-size 512 \
    --region us-west-2
Set Environment Variables
bashaws lambda update-function-configuration \
    --function-name orcutt-chat-handler \
    --environment Variables='{
        "KNOWLEDGE_BASE_ID":"your-kb-id",
        "DYNAMODB_TABLE":"orcutt-chat-conversations",
        "GUARDRAIL_ID":"your-guardrail-id",
        "GUARDRAIL_VERSION":"1"
    }' \
    --region us-west-2
4. API Gateway Setup
bash# Create API Gateway (via AWS Console recommended)
# 1. Go to API Gateway Console
# 2. Create REST API
# 3. Create resource '/chat'
# 4. Create POST method
# 5. Set Lambda integration
# 6. Enable CORS
# 7. Deploy to 'prod' stage
# 8. Note the API Gateway URL
Frontend Deployment
1. Amplify Initialization
bash# Navigate to React project root
cd orcutt-schools-chatbot

# Initialize Amplify
amplify init

# Follow prompts:
# - Project name: orcutt-schools-chatbot
# - Environment: dev (or prod)
# - Default editor: Visual Studio Code
# - App type: javascript
# - Framework: react
# - Source directory: src
# - Build command: npm run build
# - Start command: npm start
2. Configure Environment Variables
bash# Create .env.local file
cat > .env.local << EOF
REACT_APP_API_URL=https://your-api-id.execute-api.us-west-2.amazonaws.com/prod
REACT_APP_REGION=us-west-2
EOF
3. Add Authentication (Optional)
bash# Add Cognito authentication
amplify add auth

# Choose:
# - Default configuration
# - Username
# - No advanced settings
4. Add Hosting
bash# Add hosting
amplify add hosting

# Choose:
# - Amazon CloudFront and S3
# - PROD (S3 with CloudFront using HTTPS)
5. Deploy Backend and Frontend
bash# Deploy everything
amplify publish

# This will:
# - Build React app
# - Deploy to S3
# - Configure CloudFront
# - Provide domain URL
Custom Domain Setup
1. Request SSL Certificate
bash# Request certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
    --domain-name yourdomain.com \
    --domain-name www.yourdomain.com \
    --validation-method DNS \
    --region us-east-1
2. Validate Certificate
bash# Get validation records
aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID \
    --region us-east-1

# Add CNAME records to Route 53 for validation
3. Configure Custom Domain
bash# Via Amplify Console:
# 1. Go to Domain management
# 2. Add domain
# 3. Configure DNS records in Route 53
# 4. Wait for propagation (5-30 minutes)
Environment Configuration
Development Environment
bash# Create dev environment
amplify env add dev

# Use separate resources for testing
# Lower-cost configurations
# Debug logging enabled
Production Environment
bash# Create production environment
amplify env add prod

# Production configurations:
# - Enhanced performance settings
# - Production logging levels
# - Backup and monitoring enabled