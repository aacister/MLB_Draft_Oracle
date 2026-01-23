#!/usr/bin/env bash
# Deploy MCP Lambda Functions using Docker images
# Compatible with: Linux, macOS, Windows (Git Bash, WSL)

set -e

# Configuration
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-2"
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$ACCOUNT_ID" ]; then
    echo "ERROR: Failed to retrieve AWS Account ID. Please check your AWS credentials."
    echo "Run 'aws configure' or set AWS credentials via environment variables."
    exit 1
fi

ECR_REPO_NAME="mlb-draft-oracle-mcp"
ECR_REPO_URL="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

# Validate ECR_REPO_URL is properly formed
if [[ ! "$ECR_REPO_URL" =~ ^[0-9]+\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/ ]]; then
    echo "ERROR: Invalid ECR repository URL format: $ECR_REPO_URL"
    echo "Please check AWS_REGION and ACCOUNT_ID values."
    exit 1
fi

echo "Deploying MCP Lambda Functions via Docker"
echo "=========================================="
echo "AWS Region: $AWS_REGION"
echo "AWS Account: $ACCOUNT_ID"
echo "ECR Repository: $ECR_REPO_URL"
echo ""

# Step 1: Create ECR repository if it doesn't exist
echo "Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "Creating ECR repository: ${ECR_REPO_NAME}"
    aws ecr create-repository \
        --repository-name "${ECR_REPO_NAME}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true
    echo "ECR repository created"
else
    echo "ECR repository already exists"
fi

# Step 2: Login to ECR
echo ""
echo "Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
echo "Logged into ECR"

# Step 3: Build Docker image
echo ""
echo "Building Docker image..."
docker build \
    --platform linux/amd64 \
    -t "${ECR_REPO_NAME}:latest" \
    -f Dockerfile.mcp \
    .
echo "Docker image built"

# Step 4: Tag images for each MCP service
echo ""
echo "Tagging images..."
docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URL}:draft-latest"
docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URL}:knowledgebase-latest"
docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URL}:brave-search-latest"
docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URL}:latest"
echo "Images tagged"

# Step 5: Push images to ECR
echo ""
echo "Pushing images to ECR..."
docker push "${ECR_REPO_URL}:draft-latest"
docker push "${ECR_REPO_URL}:knowledgebase-latest"
docker push "${ECR_REPO_URL}:brave-search-latest"
docker push "${ECR_REPO_URL}:latest"
echo "Images pushed to ECR"

# Step 6: Deploy Lambda functions with Terraform (if Terraform is installed)
echo ""
if command -v terraform &> /dev/null; then
    echo "Deploying Lambda functions with Terraform..."
    cd infrastructure || { echo "Error: infrastructure directory not found"; exit 1; }
    
    if [ ! -d ".terraform" ]; then
        echo "Initializing Terraform..."
        terraform init
    fi
    
    echo "Planning deployment..."
    terraform plan -out=mcp-plan
    
    echo "Applying deployment..."
    terraform apply mcp-plan
    
    echo ""
    echo "Terraform deployment complete!"
    echo ""
    echo "Lambda Functions:"
    terraform output mcp_draft_lambda_arn || echo "Output not available"
    terraform output mcp_knowledgebase_lambda_arn || echo "Output not available"
    terraform output mcp_brave_search_lambda_arn || echo "Output not available"
    
    cd ..
else
    echo "WARNING: Terraform not found. Skipping Lambda deployment."
    echo "Install Terraform or deploy manually."
fi

# Step 7: Update Lambda function images (alternative to Terraform)
if [ "$1" = "manual" ]; then
    echo ""
    echo "Updating Lambda functions manually..."
    
    # Update draft server
    echo "Updating mlb-draft-oracle-mcp-draft..."
    aws lambda update-function-code \
        --function-name mlb-draft-oracle-mcp-draft \
        --image-uri "${ECR_REPO_URL}:draft-latest" \
        --region "${AWS_REGION}" 2>&1 || echo "WARNING: Function doesn't exist yet - create with Terraform first"
    
    # Update knowledgebase server
    echo "Updating mlb-draft-oracle-mcp-knowledgebase..."
    aws lambda update-function-code \
        --function-name mlb-draft-oracle-mcp-knowledgebase \
        --image-uri "${ECR_REPO_URL}:knowledgebase-latest" \
        --region "${AWS_REGION}" 2>&1 || echo "WARNING: Function doesn't exist yet - create with Terraform first"
    
    # Update brave search server
    echo "Updating mlb-draft-oracle-mcp-brave-search..."
    aws lambda update-function-code \
        --function-name mlb-draft-oracle-mcp-brave-search \
        --image-uri "${ECR_REPO_URL}:brave-search-latest" \
        --region "${AWS_REGION}" 2>&1 || echo "WARNING: Function doesn't exist yet - create with Terraform first"
    
    echo "Lambda functions updated"
fi

# Step 8: Test deployments
echo ""
echo "Testing MCP Lambda functions..."

# Create temp directory for test outputs (Windows compatible)
TEMP_DIR="${TMPDIR:-/tmp}"
mkdir -p "${TEMP_DIR}" 2>/dev/null || TEMP_DIR="."

echo "Testing draft server..."
aws lambda invoke \
    --function-name mlb-draft-oracle-mcp-draft \
    --payload '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    --region "${AWS_REGION}" \
    "${TEMP_DIR}/draft-test.json" 2>&1 && cat "${TEMP_DIR}/draft-test.json" | jq . 2>/dev/null || echo "WARNING: Test failed - function may not exist yet"

echo ""
echo "Testing knowledgebase server..."
aws lambda invoke \
    --function-name mlb-draft-oracle-mcp-knowledgebase \
    --payload '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    --region "${AWS_REGION}" \
    "${TEMP_DIR}/kb-test.json" 2>&1 && cat "${TEMP_DIR}/kb-test.json" | jq . 2>/dev/null || echo "WARNING: Test failed - function may not exist yet"

echo ""
echo "Testing brave search server..."
aws lambda invoke \
    --function-name mlb-draft-oracle-mcp-brave-search \
    --payload '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    --region "${AWS_REGION}" \
    "${TEMP_DIR}/brave-test.json" 2>&1 && cat "${TEMP_DIR}/brave-test.json" | jq . 2>/dev/null || echo "WARNING: Test failed - function may not exist yet"

echo ""
echo "Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Update main Lambda environment variables"
echo "2. Grant invoke permissions to main Lambda"
echo "3. Test full draft flow"
echo ""
echo "ECR Repository: ${ECR_REPO_URL}"
echo "Images:"
echo "  - ${ECR_REPO_URL}:draft-latest"
echo "  - ${ECR_REPO_URL}:knowledgebase-latest"
echo "  - ${ECR_REPO_URL}:brave-search-latest"