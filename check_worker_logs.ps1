# Check Worker Lambda CloudWatch Logs
# PowerShell version for Windows
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$LOG_GROUP = "/aws/lambda/mlb-draft-oracle-worker"
$REGION = "us-east-2"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Checking Worker Lambda Logs" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Get all log streams sorted by time
Write-Host "Fetching recent log streams..."
$streams = aws logs describe-log-streams `
  --log-group-name $LOG_GROUP `
  --region $REGION `
  --order-by LastEventTime `
  --descending `
  --max-items 5 `
  --query 'logStreams[*].[logStreamName,lastEventTime]' `
  --output json | ConvertFrom-Json

if (-not $streams) {
    Write-Host "❌ No log streams found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Checking if log group exists..."
    aws logs describe-log-groups `
      --log-group-name-prefix "/aws/lambda/mlb-draft-oracle" `
      --region $REGION `
      --query 'logGroups[*].logGroupName' `
      --output text
    exit 1
}

Write-Host "Recent log streams:" -ForegroundColor Green
$streams | ForEach-Object { 
    $streamName = $_[0]
    $timestamp = $_[1]
    Write-Host "  $streamName (Time: $timestamp)"
}
Write-Host ""

# Get the most recent stream
$LATEST_STREAM = $streams[0][0]
$LATEST_TIME = $streams[0][1]

Write-Host "Latest stream: $LATEST_STREAM" -ForegroundColor Yellow
$date = [DateTimeOffset]::FromUnixTimeMilliseconds($LATEST_TIME).LocalDateTime
Write-Host "Last event: $date" -ForegroundColor Yellow
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Fetching logs from latest stream..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Get logs
$events = aws logs get-log-events `
  --log-group-name $LOG_GROUP `
  --log-stream-name $LATEST_STREAM `
  --region $REGION `
  --start-from-head `
  --query 'events[*].message' `
  --output json | ConvertFrom-Json

$events | ForEach-Object {
    Write-Host $_
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "End of logs" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan