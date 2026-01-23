# Create Worker Lambda Function from Docker Image
$ErrorActionPreference = "Continue"

Write-Host "================================================"
Write-Host "Creating Worker Lambda Function"
Write-Host "================================================"

# Configuration
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$AWS_REGION = "us-east-2"
$REPOSITORY_NAME = "mlb-draft-oracle-lambda"
$ECR_URL = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}{REPOSITORY_NAME}:latest"
$WORKER_FUNCTION_NAME = "mlb-draft-oracle-worker"
$MAIN_FUNCTION_NAME = "mlb-draft-oracle"

# 1. Get the main Lambda's configuration
Write-Host "Getting main Lambda configuration..."
$mainConfigRaw = aws lambda get-function-configuration --function-name $MAIN_FUNCTION_NAME
$mainConfig = $mainConfigRaw | ConvertFrom-Json

$MAIN_LAMBDA_ROLE = $mainConfig.Role
$MAIN_LAMBDA_SUBNETS = $mainConfig.VpcConfig.SubnetIds -join ","
$MAIN_LAMBDA_SECURITY_GROUPS = $mainConfig.VpcConfig.SecurityGroupIds -join ","
$MAIN_LAMBDA_ENV = $mainConfig.Environment.Variables | ConvertTo-Json -Compress

# 2. Check if worker Lambda already exists
$functionExists = $false
try {
    aws lambda get-function --function-name $WORKER_FUNCTION_NAME --query 'Configuration.FunctionName' --output text 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $functionExists = $true }
} catch {
    $functionExists = $false
}

if ($functionExists) {
    Write-Host "Worker Lambda already exists. Updating..."
    aws lambda update-function-code --function-name $WORKER_FUNCTION_NAME --image-uri $ECR_URL
    aws lambda wait function-updated --function-name $WORKER_FUNCTION_NAME
    
    aws lambda update-function-configuration `
      --function-name $WORKER_FUNCTION_NAME `
      --image-config "Command=backend.api.lambda_handler_worker.handler"
} else {
    Write-Host "Creating new worker Lambda..."
    aws lambda create-function `
      --function-name $WORKER_FUNCTION_NAME `
      --role $MAIN_LAMBDA_ROLE `
      --package-type Image `
      --code ImageUri=$ECR_URL `
      --timeout 900 `
      --memory-size 2048 `
      --environment "Variables=$MAIN_LAMBDA_ENV" `
      --vpc-config "SubnetIds=[$MAIN_LAMBDA_SUBNETS],SecurityGroupIds=[$MAIN_LAMBDA_SECURITY_GROUPS]" `
      --image-config "Command=backend.api.lambda_handler_worker.handler"
    
    aws lambda wait function-active --function-name $WORKER_FUNCTION_NAME
}

# 3. Grant Permissions
Write-Host "Checking permissions..."
$policyExists = $false
try {
    $policyRaw = aws lambda get-policy --function-name $WORKER_FUNCTION_NAME 2>$null
    if ($null -ne $policyRaw -and $policyRaw -like "*AllowMainLambdaInvoke*") { $policyExists = $true }
} catch {
    $policyExists = $false
}

if (-not $policyExists) {
    Write-Host "Adding invoke permission..."
    $MAIN_LAMBDA_ARN = (aws lambda get-function --function-name $MAIN_FUNCTION_NAME | ConvertFrom-Json).Configuration.FunctionArn
    aws lambda add-permission `
      --function-name $WORKER_FUNCTION_NAME `
      --statement-id AllowMainLambdaInvoke `
      --action lambda:InvokeFunction `
      --principal lambda.amazonaws.com `
      --source-arn $MAIN_LAMBDA_ARN
} else {
    Write-Host "Permission already exists."
}

# 4. Testing
Write-Host "Testing Worker Lambda..."
$testPayload = '{"action":"execute_draft_pick","draft_id":"test-draft-id","team_name":"TestTeam","round":1,"pick":1}'
$payloadPath = "$env:TEMP\test_worker_payload.json"
$responsePath = "$env:TEMP\test_response.json"

[System.IO.File]::WriteAllText($payloadPath, $testPayload)

aws lambda invoke `
  --function-name $WORKER_FUNCTION_NAME `
  --invocation-type RequestResponse `
  --payload "file://$payloadPath" `
  --cli-binary-format raw-in-base64-out `
  $responsePath

if (Test-Path $responsePath) {
    Write-Host "Response received:"
    Get-Content $responsePath | ConvertFrom-Json | ConvertTo-Json
}

Write-Host "================================================"
Write-Host "Setup Complete!"
Write-Host "================================================"
