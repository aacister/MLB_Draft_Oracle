# Rebuild the Docker image
docker build -f Dockerfile.worker_lambda -t mlb-draft-oracle-worker:latest .

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-2"
REPOSITORY_NAME="mlb-draft-oracle-worker"

# Get ECR repository URL (from Terraform output or manually)
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_URL}

# Tag and push
docker tag mlb-draft-oracle-worker:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest


# Update Lambda function to use new image
aws lambda update-function-code \
    --function-name mlb-draft-oracle-worker \
    --image-uri ${ECR_URL}:latest

# Wait for update to complete
aws lambda wait function-updated \
    --function-name mlb-draft-oracle-worker

echo "Lambda function updated successfully!"