#!/usr/bin/env bash
ACCOUNT_ID="425865275846"
REGION="us-east-2"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}"

echo "Logged in to ${REGISTRY}"