export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_URL="$ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/mlb-draft-oracle-mcp"

# Login
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com


# Rebuild
docker build --no-cache --platform linux/amd64 -t mlb-draft-oracle-mcp:latest -f Dockerfile.mcp .

# Tag and push
export ECR_URL="$ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/mlb-draft-oracle-mcp"
docker tag mlb-draft-oracle-mcp:latest ${ECR_URL}:draft-latest
docker tag mlb-draft-oracle-mcp:latest ${ECR_URL}:knowledgebase-latest
docker tag mlb-draft-oracle-mcp:latest ${ECR_URL}:brave-search-latest
docker push ${ECR_URL}:draft-latest
docker push ${ECR_URL}:knowledgebase-latest
docker push ${ECR_URL}:brave-search-latest