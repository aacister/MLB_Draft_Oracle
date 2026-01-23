# Add these variables to your existing variables.tf file

variable "route_table_ids" {
  description = "List of route table IDs for S3 gateway endpoint"
  type        = list(string)
  # Get these from your VPC - run: 
  # aws ec2 describe-route-tables --filters "Name=vpc-id,Values=YOUR_VPC_ID" --query 'RouteTables[*].RouteTableId' --output text
}

# If you don't have these already:
variable "vpc_id" {
  description = "VPC ID where Lambda functions are deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for Lambda functions"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}