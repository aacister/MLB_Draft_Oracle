ACCOUNT_ID="425865275846"
REGION="us-east-2"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Remove old images
docker rmi mlb-draft-oracle-mcp:latest -f
docker rmi $ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/mlb-draft-oracle-mcp:draft-latest -f

# Rebuild with no cache
docker build --no-cache --platform linux/amd64 -t mlb-draft-oracle-mcp:latest -f Dockerfile.mcp .

# Verify the build completed successfully
echo "Build complete - checking image..."