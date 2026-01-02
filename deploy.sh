#!/bin/bash
set -e

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="425865275846"
REPOSITORY_NAME="mlb-draft-oracle-lambda"
IMAGE_TAG="latest"

echo "=== Step 1: Create ECR Repository with Terraform ==="
cd terraform
terraform init
terraform apply -target=aws_ecr_repository.mlb_draft_oracle -auto-approve
cd ..

echo "=== Step 2: Build and Push Docker Image ==="
# Get ECR repository URL from Terraform output
ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)

# Authenticate with ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_URL}

# Build image
echo "Building Docker image..."
docker build -f Dockerfile.lambda -t ${REPOSITORY_NAME}:${IMAGE_TAG} .

# Tag image
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URL}:${IMAGE_TAG}

# Push to ECR
echo "Pushing to ECR..."
docker push ${ECR_URL}:${IMAGE_TAG}

echo "=== Step 3: Deploy Lambda and API Gateway ==="
cd terraform
terraform apply -auto-approve
cd ..

echo "=== Deployment Complete ==="
echo "API Gateway URL:"
cd terraform && terraform output api_gateway_url