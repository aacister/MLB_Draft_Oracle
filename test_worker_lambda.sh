#!/bin/bash

# Configuration
DRAFT_ID="63e5a3b0-a9c6-4051-b14d-2e222adc6979"
TEAM_NAME="HomeRunAlone"
ROUND=3
PICK=6
FUNCTION_NAME="mlb-draft-oracle-worker"
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Create payload
cat > worker_payload.json <<EOF
{
  "action": "execute_draft_pick",
  "draft_id": "${DRAFT_ID}",
  "team_name": "${TEAM_NAME}",
  "round": ${ROUND},
  "pick": ${PICK}
}
EOF

echo "Test 1: Synchronous Invocation"
# ADDED: --cli-binary-format raw-in-base64-out
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --invocation-type RequestResponse \
  --cli-binary-format raw-in-base64-out \
  --payload file://worker_payload.json \
  worker_response.json

echo "Response:"
cat worker_response.json
echo -e "\n"

echo "Test 2: Checking CloudWatch Logs..."
# Use MSYS_NO_PATHCONV to prevent Git Bash from changing the log group path
LATEST_STREAM=$(MSYS_NO_PATHCONV=1 aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text)

if [ "$LATEST_STREAM" != "None" ] && [ -n "$LATEST_STREAM" ]; then
    echo "Latest stream: $LATEST_STREAM"
    MSYS_NO_PATHCONV=1 aws logs get-log-events \
      --log-group-name "$LOG_GROUP" \
      --log-stream-name "$LATEST_STREAM" \
      --limit 10 \
      --query 'events[*].message' \
      --output text
else
    echo "No log stream found. Ensure the Lambda has permissions to create logs."
fi
