# Fixed VPC Endpoint Creation Script for Lambda (2026)
$ErrorActionPreference = "Stop"
$REGION = "us-east-2"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Creating VPC Endpoints for Lambda" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# 1. Retrieve Lambda VPC Configuration
Write-Host "Getting Lambda VPC configuration..." -ForegroundColor Yellow
$lambdaConfig = aws lambda get-function-configuration --function-name mlb-draft-oracle-worker --output json | ConvertFrom-Json

$VPC_ID = $lambdaConfig.VpcConfig.VpcId
$SUBNET_IDS = $lambdaConfig.VpcConfig.SubnetIds
$LAMBDA_SG = $lambdaConfig.VpcConfig.SecurityGroupIds[0]

# 2. Setup Security Group
$VPC_CIDR = aws ec2 describe-vpcs --vpc-ids $VPC_ID --query 'Vpcs[0].CidrBlock' --output text

try {
    $ENDPOINTS_SG = aws ec2 create-security-group `
        --group-name "mlb-draft-oracle-vpc-endpoints" `
        --description "Security group for VPC endpoints" `
        --vpc-id $VPC_ID `
        --output text
    
    aws ec2 authorize-security-group-ingress --group-id $ENDPOINTS_SG --protocol tcp --port 443 --cidr $VPC_CIDR
    Write-Host "✓ Security group created: $ENDPOINTS_SG" -ForegroundColor Green
}
catch {
    $ENDPOINTS_SG = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=mlb-draft-oracle-vpc-endpoints" "Name=vpc-id,Values=$VPC_ID" `
        --query 'SecurityGroups[0].GroupId' --output text
    Write-Host "Using existing security group: $ENDPOINTS_SG" -ForegroundColor Green
}

# 3. Corrected Function Definition
function Create-VPCEndpoint {
    param (
        [string]$ServiceName,
        [string]$DisplayName
    )
    
    Write-Host "Creating $DisplayName endpoint..." -ForegroundColor Yellow
    $fullServiceName = "com.amazonaws.$REGION.$ServiceName"
    
    try {
        # Using a single-line command or splatting prevents line-continuation errors
        $endpoint = aws ec2 create-vpc-endpoint --vpc-id $VPC_ID --vpc-endpoint-type Interface --service-name $fullServiceName --subnet-ids $SUBNET_IDS --security-group-ids $ENDPOINTS_SG --private-dns-enabled --output json | ConvertFrom-Json
        Write-Host "✓ $DisplayName created: $($endpoint.VpcEndpoint.VpcEndpointId)" -ForegroundColor Green
    }
    catch {
        Write-Host "  Note: Skipping $DisplayName (likely already exists or region error)." -ForegroundColor Yellow
    }
} # Closing brace for function

# 4. Create Interface Endpoints
$services = @{
    "secretsmanager" = "Secrets Manager"
    "rds"            = "RDS"
    "lambda"         = "Lambda"
    "logs"           = "CloudWatch Logs"
    "ecr.api"        = "ECR API"
    "ecr.dkr"        = "ECR Docker"
}

foreach ($key in $services.Keys) {
    Create-VPCEndpoint -ServiceName $key -DisplayName $services[$key]
    Start-Sleep -Seconds 1
}

# 5. Create S3 Gateway Endpoint
Write-Host "Creating S3 Gateway Endpoint..." -ForegroundColor Cyan
$ROUTE_TABLES = aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --query 'RouteTables[*].RouteTableId' --output json | ConvertFrom-Json

try {
    aws ec2 create-vpc-endpoint --vpc-id $VPC_ID --vpc-endpoint-type Gateway --service-name "com.amazonaws.$REGION.s3" --route-table-ids $ROUTE_TABLES
    Write-Host "✓ S3 Gateway endpoint configured." -ForegroundColor Green
}
catch {
    Write-Host "  S3 endpoint already exists or failed to attach to route tables." -ForegroundColor Yellow
}

Write-Host "VPC Endpoints Creation Complete!" -ForegroundColor Cyan