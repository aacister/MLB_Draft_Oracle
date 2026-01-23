# Rebuild worker
#docker build --platform linux/amd64 -t mlb-draft-oracle-worker:latest .
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-2"
REPOSITORY_NAME="mlb-draft-oracle-worker"

# Get ECR repository URL (from Terraform output or manually)
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"
# Tag and push

docker tag mlb-draft-oracle-worker:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest

# Update Lambda
aws lambda update-function-code \
    --function-name mlb-draft-oracle-worker \
    --image-uri ${ECR_URL}:latest