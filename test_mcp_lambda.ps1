# PowerShell script to invoke MLB Draft Oracle MCP Lambda function
# This script first lists available tools, then calls the search tool

# Configuration
$FunctionName = "mlb-draft-oracle-mcp-draft"
$Region = "us-east-2"

# Resolve absolute paths to ensure AWS CLI can find the files
$workingDir = Get-Location
$payloadFile = Join-Path $workingDir "payload.json"
$responseFile = Join-Path $workingDir "response.json"

# Function to write JSON payload without BOM
function Write-JsonPayload {
    param([string]$Content, [string]$FilePath)
    
    try {
        $utf8NoBomEncoding = New-Object System.Text.UTF8Encoding($false)
        $sw = New-Object System.IO.StreamWriter($FilePath, $false, $utf8NoBomEncoding)
        $sw.Write($Content)
        $sw.Close()
    }
    catch {
        Write-Host "Failed to write payload file: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Function to invoke Lambda
function Invoke-McpLambda {
    param([string]$RequestJson)
    
    Write-JsonPayload -Content $RequestJson -FilePath $payloadFile
    
    $payloadArg = "file://$payloadFile"
    
    aws lambda invoke `
        --function-name $FunctionName `
        --region $Region `
        --payload "$payloadArg" `
        --cli-binary-format raw-in-base64-out `
        "$responseFile" | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Lambda invocation failed with exit code: $LASTEXITCODE"
    }

    if (Test-Path $responseFile) {
        $responseContent = Get-Content $responseFile -Raw
        return ($responseContent | ConvertFrom-Json)
    }
    else {
        throw "No response file generated at $responseFile"
    }
}

try {
    # Step 1: List available tools
    Write-Host "=== Step 1: Listing Available Tools ===" -ForegroundColor Cyan
    
    $listToolsRequest = @{
        jsonrpc = "2.0"
        id = 1
        method = "tools/list"
        params = @{}
    } | ConvertTo-Json -Depth 10 -Compress

    Write-Host "Request:" -ForegroundColor Yellow
    Write-Host $listToolsRequest
    Write-Host "`nInvoking Lambda..." -ForegroundColor Cyan
    
    $listResponse = Invoke-McpLambda -RequestJson $listToolsRequest
    
    Write-Host "`nRaw Response:" -ForegroundColor Green
    Write-Host ($listResponse | ConvertTo-Json -Depth 10)

    if ($listResponse.error) {
        Write-Host "`nMCP Error:" -ForegroundColor Red
        Write-Host ($listResponse.error | ConvertTo-Json -Depth 10)
        throw "Failed to list tools"
    }

    # Display available tools
    if ($listResponse.result -and $listResponse.result.tools) {
        Write-Host "`nAvailable Tools:" -ForegroundColor Magenta
        foreach ($tool in $listResponse.result.tools) {
            Write-Host "  - Name: $($tool.name)" -ForegroundColor Green
            if ($tool.description) {
                Write-Host "    Description: $($tool.description)" -ForegroundColor Gray
            }
            if ($tool.inputSchema -and $tool.inputSchema.properties) {
                Write-Host "    Parameters:" -ForegroundColor Gray
                foreach ($prop in $tool.inputSchema.properties.PSObject.Properties) {
                    $required = if ($tool.inputSchema.required -contains $prop.Name) { " (required)" } else { "" }
                    Write-Host "      - $($prop.Name)$required" -ForegroundColor DarkGray
                }
            }
            Write-Host ""
        }
        
        # Step 2: Find and call the search tool
        $searchTool = $listResponse.result.tools | Where-Object { 
            $_.name -like "*search*" -or $_.name -like "*brave*" 
        } | Select-Object -First 1
        
        if ($searchTool) {
            Write-Host "`n=== Step 2: Calling Search Tool: $($searchTool.name) ===" -ForegroundColor Cyan
            
            # Build arguments based on the tool's input schema
            $searchArgs = @{
                query = "2026 MLB Draft prospects top players"
            }
            
            # Add optional parameters if they exist in the schema
            if ($searchTool.inputSchema.properties.count) {
                $searchArgs.count = 10
            }
            if ($searchTool.inputSchema.properties.limit) {
                $searchArgs.limit = 10
            }
            
            $searchRequest = @{
                jsonrpc = "2.0"
                id = 2
                method = "tools/call"
                params = @{
                    name = $searchTool.name
                    arguments = $searchArgs
                }
            } | ConvertTo-Json -Depth 10 -Compress
            
            Write-Host "Search Request:" -ForegroundColor Yellow
            Write-Host $searchRequest
            Write-Host "`nInvoking Lambda with search..." -ForegroundColor Cyan
            
            $searchResponse = Invoke-McpLambda -RequestJson $searchRequest
            
            Write-Host "`nRaw Search Response:" -ForegroundColor Green
            Write-Host ($searchResponse | ConvertTo-Json -Depth 10)

            if ($searchResponse.error) {
                Write-Host "`nMCP Error:" -ForegroundColor Red
                Write-Host ($searchResponse.error | ConvertTo-Json -Depth 10)
            }
            elseif ($searchResponse.result -and $searchResponse.result.content) {
                Write-Host "`nSearch Results:" -ForegroundColor Magenta
                foreach ($content in $searchResponse.result.content) {
                    if ($content.type -eq "text") {
                        Write-Host $content.text -ForegroundColor White
                    }
                }
            }
        }
        else {
            Write-Host "`nNo search tool found in available tools." -ForegroundColor Yellow
            Write-Host "Please check your MCP server configuration." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "`nNo tools found or unexpected response format." -ForegroundColor Yellow
    }
}
catch {
    Write-Host "`nError:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
}
finally {
    # Clean up temp files
    if (Test-Path $payloadFile) { Remove-Item $payloadFile -ErrorAction SilentlyContinue }
    if (Test-Path $responseFile) { Remove-Item $responseFile -ErrorAction SilentlyContinue }
}

Write-Host "`n=== Script Execution Finished ===" -ForegroundColor Cyan