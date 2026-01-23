# Fix Worker Lambda Handler for Docker Image Type
Write-Host "================================================"
Write-Host "Fixing Worker Lambda (Docker Image Type)"
Write-Host "================================================"

$WORKER_FUNCTION = "mlb-draft-oracle-worker"

# 1. Check current configuration
Write-Host "Current configuration:"
$config = aws lambda get-function-configuration --function-name $WORKER_FUNCTION | ConvertFrom-Json
$config | Select-Object PackageType, ImageConfig | ConvertTo-Json
Write-Host ""

# 2. Update the image config to override CMD
Write-Host "Updating image configuration..."

# Fix: Use single quotes for the parameter and backslash to escape internal quotes
aws lambda update-function-configuration `
    --function-name $WORKER_FUNCTION `
    --image-config '{\"Command\":[\"backend.api.lambda_handler_worker.handler\"]}'

Write-Host ""
Write-Host "Waiting for update to complete..."
Start-Sleep -Seconds 10

# 3. Verify the update
Write-Host "New configuration:"
$newConfig = aws lambda get-function-configuration --function-name $WORKER_FUNCTION | ConvertFrom-Json
$newConfig | Select-Object PackageType, ImageConfig | ConvertTo-Json
Write-Host ""

Write-Host "================================================"
Write-Host "Configuration updated!"
Write-Host "================================================"
Write-Host ""
Write-Host "Now test with:"
Write-Host ".\test_worker_lambda.ps1"
