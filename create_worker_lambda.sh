#!/bin/bash

# Create Worker Lambda Function from Docker Image
# This creates a separate Lambda that uses the same Docker image but different handler

set -e

echo "================================================"
echo "Creating Worker Lambda Function"
echo "================================================"

# Configuration
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-2"
REPOSITORY_NAME="mlb-draft-oracle-lambda"
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}:latest"
WORKER_FUNCTION_NAME="mlb-draft-oracle-worker"

# Get the main Lambda's configuration for reference
echo "Getting main Lambda configuration..."
MAIN_LAMBDA_ROLE=$(aws lambda get-function-configuration \
  --function-name mlb-draft-oracle \
  --query 'Role' \
  --output text)

MAIN_LAMBDA_SUBNETS=$(aws lambda get-function-configuration \
  --function-name mlb-draft-oracle \
  --query 'VpcConfig.SubnetIds' \
  --output json)

MAIN_LAMBDA_SECURITY_GROUPS=$(aws lambda get-function-configuration \
  --function-name mlb-draft-oracle \
  --query 'VpcConfig.SecurityGroupIds' \
  --output json)

MAIN_LAMBDA_ENV=$(aws lambda get-function-configuration \
  --function-name mlb-draft-oracle \
  --query 'Environment.Variables' \
  --output json)

echo "Main Lambda Role: $MAIN_LAMBDA_ROLE"
echo "Subnets: $MAIN_LAMBDA_SUBNETS"
echo "Security Groups: $MAIN_LAMBDA_SECURITY_GROUPS"
echo ""

# Check if worker Lambda already exists
if aws lambda get-function --function-name "$WORKER_FUNCTION_NAME" 2>/dev/null; then
    echo "Worker Lambda already exists. Updating configuration..."
    
    # Update the function code (image URI)
    aws lambda update-function-code \
      --function-name "$WORKER_FUNCTION_NAME" \
      --image-uri "$ECR_URL"
    
    echo "Waiting for code update..."
    aws lambda wait function-updated --function-name "$WORKER_FUNCTION_NAME"
    
    # Update the image config to use worker handler
    aws lambda update-function-configuration \
      --function-name "$WORKER_FUNCTION_NAME" \
      --image-config '{"Command":["backend.api.lambda_handler_worker.handler"]}'
    
    echo "Waiting for config update..."
    sleep 10
    
    echo "✓ Worker Lambda updated"
else
    echo "Creating new worker Lambda..."
    
    # Create the worker Lambda function
    aws lambda create-function \
      --function-name "$WORKER_FUNCTION_NAME" \
      --role "$MAIN_LAMBDA_ROLE" \
      --package-type Image \
      --code ImageUri="$ECR_URL" \
      --timeout 900 \
      --memory-size 2048 \
      --environment "Variables=$MAIN_LAMBDA_ENV" \
      --vpc-config SubnetIds="$MAIN_LAMBDA_SUBNETS",SecurityGroupIds="$MAIN_LAMBDA_SECURITY_GROUPS" \
      --image-config '{"Command":["backend.api.lambda_handler_worker.handler"]}'
    
    echo "Waiting for function to be active..."
    aws lambda wait function-active --function-name "$WORKER_FUNCTION_NAME"
    
    echo "✓ Worker Lambda created"
fi

echo ""
echo "================================================"
echo "Verifying Configuration"
echo "================================================"

aws lambda get-function-configuration \
  --function-name "$WORKER_FUNCTION_NAME" \
  | jq '{
    FunctionName: .FunctionName,
    PackageType: .PackageType,
    ImageUri: .CodeSha256,
    Handler: .Handler,
    ImageConfig: .ImageConfig,
    Timeout: .Timeout,
    MemorySize: .MemorySize,
    State: .State
  }'

echo ""
echo "================================================"
echo "Granting Invoke Permissions"
echo "================================================"

# Grant main Lambda permission to invoke worker
# First, check if the permission already exists
POLICY_EXISTS=$(aws lambda get-policy \
  --function-name "$WORKER_FUNCTION_NAME" 2>/dev/null \
  | jq -r '.Policy' \
  | jq 'select(.Statement[].Sid == "AllowMainLambdaInvoke")' 2>/dev/null || echo "")

if [ -z "$POLICY_EXISTS" ]; then
    echo "Adding invoke permission for main Lambda..."
    
    MAIN_LAMBDA_ARN=$(aws lambda get-function \
      --function-name mlb-draft-oracle \
      --query 'Configuration.FunctionArn' \
      --output text)
    
    aws lambda add-permission \
      --function-name "$WORKER_FUNCTION_NAME" \
      --statement-id AllowMainLambdaInvoke \
      --action lambda:InvokeFunction \
      --principal lambda.amazonaws.com \
      --source-arn "$MAIN_LAMBDA_ARN"
    
    echo "✓ Permission added"
else
    echo "✓ Permission already exists"
fi

echo ""
echo "================================================"
echo "Testing Worker Lambda"
echo "================================================"

# Create test payload
cat > /tmp/test_worker_payload.json <<EOF
{
  "action": "execute_draft_pick",
  "draft_id": "test-draft-id",
  "team_name": "TestTeam",
  "round": 1,
  "pick": 1
}
EOF

echo "Test payload:"
cat /tmp/test_worker_payload.json
echo ""

echo "Invoking worker Lambda (this may take 30-60 seconds)..."
aws lambda invoke \
  --function-name "$WORKER_FUNCTION_NAME" \
  --invocation-type RequestResponse \
  --payload file:///tmp/test_worker_payload.json \
  --log-type Tail \
  /tmp/test_response.json

echo ""
echo "Response:"
cat /tmp/test_response.json | jq .

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Worker Lambda: $WORKER_FUNCTION_NAME"
echo "Image: $ECR_URL"
echo "Handler: backend.api.lambda_handler_worker.handler"
echo ""
echo "To test with real draft:"
echo "  Update draft_id, team_name, round, pick in test payload"
echo "  Then run: ./test_worker_lambda.sh"