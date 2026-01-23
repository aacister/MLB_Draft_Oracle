# Terraform configuration for MCP Lambda functions using Docker images
# Updated to use container images instead of ZIP files

# ECR Repository for MCP Lambda images (if you don't have one already)
resource "aws_ecr_repository" "mcp_lambda" {
  name                 = "mlb-draft-oracle-mcp"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name        = "MCP Lambda Container Repository"
    Environment = "production"
    Service     = "mlb-draft-oracle"
  }
}

# MCP Draft Server Lambda (using Docker image)
resource "aws_lambda_function" "mcp_draft_server" {
  function_name = "mlb-draft-oracle-mcp-draft"
  role          = aws_iam_role.mcp_lambda_role.arn
  
  # Use container image instead of ZIP
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.mcp_lambda.repository_url}:draft-latest"
  
  timeout       = 300
  memory_size   = 512
  
  # Image config specifies the handler
  image_config {
    command = ["backend.mcp_servers.draft_server_lambda_simple.handler"]
  }
  
  environment {
    variables = {
      DB_SECRET_ARN           = var.db_secret_arn
      AWS_REGION_NAME         = var.aws_region
      DEPLOYMENT_ENVIRONMENT  = "LAMBDA"
      OPENAI_API_KEY         = var.openai_api_key
    }
  }
  
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.mcp_lambda_sg.id]
  }
  
  tags = {
    Name        = "MCP Draft Server"
    Environment = "production"
    Service     = "mlb-draft-oracle"
  }
  
  # Prevent recreation when image changes
  lifecycle {
    ignore_changes = [image_uri]
  }
}

# MCP Knowledgebase Server Lambda (using Docker image)
resource "aws_lambda_function" "mcp_knowledgebase_server" {
  function_name = "mlb-draft-oracle-mcp-knowledgebase"
  role          = aws_iam_role.mcp_lambda_role.arn
  
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.mcp_lambda.repository_url}:knowledgebase-latest"
  
  timeout       = 300
  memory_size   = 512
  
  image_config {
    command = ["backend.mcp_servers.knowledgebase_server_lambda_simple.handler"]
  }
  
  environment {
    variables = {
      DB_SECRET_ARN           = var.db_secret_arn
      AWS_REGION_NAME         = var.aws_region
      DEPLOYMENT_ENVIRONMENT  = "LAMBDA"
      VECTOR_BUCKET          = var.vector_bucket
      SAGEMAKER_ENDPOINT     = var.sagemaker_endpoint
    }
  }
  
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.mcp_lambda_sg.id]
  }
  
  tags = {
    Name        = "MCP Knowledgebase Server"
    Environment = "production"
    Service     = "mlb-draft-oracle"
  }
  
  lifecycle {
    ignore_changes = [image_uri]
  }
}

# MCP Brave Search Server Lambda (using Docker image)
resource "aws_lambda_function" "mcp_brave_search_server" {
  function_name = "mlb-draft-oracle-mcp-brave-search"
  role          = aws_iam_role.mcp_lambda_role.arn
  
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.mcp_lambda.repository_url}:brave-search-latest"
  
  timeout       = 60
  memory_size   = 256
  
  image_config {
    command = ["backend.mcp_servers.brave_search_lambda_simple.handler"]
  }
  
  environment {
    variables = {
      BRAVE_API_KEY          = var.brave_api_key
      AWS_REGION_NAME        = var.aws_region
      DEPLOYMENT_ENVIRONMENT = "LAMBDA"
    }
  }
  
  tags = {
    Name        = "MCP Brave Search Server"
    Environment = "production"
    Service     = "mlb-draft-oracle"
  }
  
  lifecycle {
    ignore_changes = [image_uri]
  }
}

# IAM Role for MCP Lambdas
resource "aws_iam_role" "mcp_lambda_role" {
  name = "mlb-draft-oracle-mcp-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach policies
resource "aws_iam_role_policy_attachment" "mcp_lambda_basic" {
  role       = aws_iam_role.mcp_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "mcp_lambda_vpc" {
  role       = aws_iam_role.mcp_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "mcp_lambda_custom" {
  name = "mcp-lambda-custom-policy"
  role = aws_iam_role.mcp_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [var.db_secret_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${var.vector_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = [
          "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.sagemaker_endpoint}"
        ]
      }
    ]
  })
}

# Security group for MCP Lambdas (if using VPC)
resource "aws_security_group" "mcp_lambda_sg" {
  name        = "mlb-draft-oracle-mcp-lambda-sg"
  description = "Security group for MCP Lambda functions"
  vpc_id      = var.vpc_id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "MCP Lambda Security Group"
  }
}

data "aws_caller_identity" "current" {}

# Variables
variable "db_secret_arn" {
  description = "ARN of the database secret"
  type        = string
}

variable "vector_bucket" {
  description = "Name of the S3 vector bucket"
  type        = string
}

variable "vector_bucket_arn" {
  description = "ARN of the S3 vector bucket"
  type        = string
}

variable "sagemaker_endpoint" {
  description = "Name of the SageMaker endpoint"
  type        = string
  default     = "mlbdraftoracle-embedding-endpoint"
}

variable "brave_api_key" {
  description = "Brave Search API key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "VPC ID for Lambda functions"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda functions"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

# Outputs
output "mcp_ecr_repository_url" {
  value = aws_ecr_repository.mcp_lambda.repository_url
}

output "mcp_draft_lambda_arn" {
  value = aws_lambda_function.mcp_draft_server.arn
}

output "mcp_knowledgebase_lambda_arn" {
  value = aws_lambda_function.mcp_knowledgebase_server.arn
}

output "mcp_brave_search_lambda_arn" {
  value = aws_lambda_function.mcp_brave_search_server.arn
}