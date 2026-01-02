provider "aws" {
  region = "us-east-2"
}

# Variables
variable "brave_api_key" {
  description = "Brave API Key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

# ECR Repository
resource "aws_ecr_repository" "mlb_draft_oracle" {
  name                 = "mlb-draft-oracle-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "mlb-draft-oracle-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# Lambda Function
resource "aws_lambda_function" "mlb_draft_oracle" {
  function_name = "mlb-draft-oracle"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.mlb_draft_oracle.repository_url}:latest"
  timeout       = 900
  memory_size   = 3008

  ephemeral_storage {
    size = 10240
  }

  environment {
    variables = {
      BRAVE_API_KEY          = var.brave_api_key
      OPENAI_API_KEY         = var.openai_api_key
      DEPLOYMENT_ENVIRONMENT = "LAMBDA"
    }
  }

  depends_on = [aws_ecr_repository.mlb_draft_oracle]
}

# Lambda Function URL (for easy testing)
resource "aws_lambda_function_url" "mlb_draft_oracle" {
  function_name      = aws_lambda_function.mlb_draft_oracle.function_name
  authorization_type = "NONE"

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    max_age           = 86400
    allow_credentials = false
  }
}

# API Gateway HTTP API
resource "aws_apigatewayv2_api" "mlb_draft_oracle" {
  name          = "mlb-draft-oracle-api"
  protocol_type = "HTTP"
  description   = "MLB Draft Oracle API Gateway"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.mlb_draft_oracle.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.mlb_draft_oracle.invoke_arn

  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

# ============================================================================
# API ROUTES
# ============================================================================

# Health Check Route
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# DRAFT ROUTES
# ============================================================================

# Get current draft
resource "aws_apigatewayv2_route" "get_draft" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/draft"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Get draft by ID
resource "aws_apigatewayv2_route" "get_draft_by_id" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/drafts/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Resume draft
resource "aws_apigatewayv2_route" "resume_draft" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "POST /v1/drafts/{draft_id}/resume"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Select player (draft pick)
resource "aws_apigatewayv2_route" "select_player" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/drafts/{draft_id}/teams/{team_name}/round/{round}/pick/{pick}/select-player"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Get all drafts
resource "aws_apigatewayv2_route" "get_drafts" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/drafts"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# DRAFT HISTORY ROUTES
# ============================================================================

# Get draft history
resource "aws_apigatewayv2_route" "get_draft_history" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/draft-history/{draft_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# PLAYER POOL ROUTES
# ============================================================================

# Get player pool by ID
resource "aws_apigatewayv2_route" "get_player_pool_by_id" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/player-pools/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Get current player pool
resource "aws_apigatewayv2_route" "get_player_pool" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/player-pool"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Check player pool exists
resource "aws_apigatewayv2_route" "check_player_pool" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/player-pool/check"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# PLAYER ROUTES
# ============================================================================

# Get player by ID
resource "aws_apigatewayv2_route" "get_player" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/players/{player_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# TEAM ROUTES
# ============================================================================

# Get team by name
resource "aws_apigatewayv2_route" "get_team" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "GET /v1/drafts/{draft_id}/teams/{team_name}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# DEFAULT CATCH-ALL ROUTE (for any unmatched routes)
# ============================================================================

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.mlb_draft_oracle.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================================
# STAGE (auto-deploy)
# ============================================================================

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.mlb_draft_oracle.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }
}

# CloudWatch Log Group for API Gateway logs
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/mlb-draft-oracle"
  retention_in_days = 7
}

# ============================================================================
# LAMBDA PERMISSIONS
# ============================================================================

# Allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mlb_draft_oracle.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.mlb_draft_oracle.execution_arn}/*/*"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "ecr_repository_url" {
  value       = aws_ecr_repository.mlb_draft_oracle.repository_url
  description = "ECR Repository URL"
}

output "lambda_function_url" {
  value       = aws_lambda_function_url.mlb_draft_oracle.function_url
  description = "Lambda Function URL (Direct Access)"
}

output "api_gateway_url" {
  value       = aws_apigatewayv2_stage.default.invoke_url
  description = "API Gateway Base URL"
}

output "api_gateway_id" {
  value       = aws_apigatewayv2_api.mlb_draft_oracle.id
  description = "API Gateway ID"
}

output "lambda_function_name" {
  value       = aws_lambda_function.mlb_draft_oracle.function_name
  description = "Lambda Function Name"
}

# Output all endpoint URLs for easy reference
output "api_endpoints" {
  value = {
    health_check     = "${aws_apigatewayv2_stage.default.invoke_url}/health"
    get_draft        = "${aws_apigatewayv2_stage.default.invoke_url}/v1/draft"
    get_drafts       = "${aws_apigatewayv2_stage.default.invoke_url}/v1/drafts"
    get_player_pool  = "${aws_apigatewayv2_stage.default.invoke_url}/v1/player-pool"
    draft_history    = "${aws_apigatewayv2_stage.default.invoke_url}/v1/draft-history/{draft_id}"
  }
  description = "API Endpoint URLs"
}