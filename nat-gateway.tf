# MLB Draft Oracle - NAT Gateway Configuration
# Region: us-east-2
# Purpose: Manage NAT Gateway for cost optimization (can be destroyed/recreated easily)

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

# Data sources for existing infrastructure
data "aws_vpc" "main" {
  id = "vpc-09b885244b3a68892"
}

data "aws_subnet" "public_2a" {
  id = "subnet-018f188c413229823"
}

data "aws_subnet" "private_2a" {
  id = "subnet-0983d9791ce1811d0"
}

data "aws_route_table" "private_2a" {
  route_table_id = "rtb-0331fd9cd8bf16851"
}

data "aws_route_table" "private_2b" {
  route_table_id = "rtb-028fbce08449a8eb3"
}

data "aws_route_table" "main" {
  route_table_id = "rtb-0b8d930671e09f679"
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "mlb-draft-oracle-vpc-eip-us-east-2a"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = false
  }
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = data.aws_subnet.public_2a.id

  tags = {
    Name = "mlb-draft-oracle-vpc-nat-public1-us-east-2a"
  }

  # NAT Gateway depends on Internet Gateway
  depends_on = [aws_eip.nat]
}

# Route for private subnet 2a
resource "aws_route" "private_2a_nat" {
  route_table_id         = data.aws_route_table.private_2a.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

# Route for private subnet 2b
resource "aws_route" "private_2b_nat" {
  route_table_id         = data.aws_route_table.private_2b.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

# Route for main route table
resource "aws_route" "main_nat" {
  route_table_id         = data.aws_route_table.main.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

# Outputs
output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.main.id
}

output "nat_gateway_public_ip" {
  description = "Public IP of the NAT Gateway"
  value       = aws_eip.nat.public_ip
}

output "eip_allocation_id" {
  description = "Allocation ID of the Elastic IP"
  value       = aws_eip.nat.id
}

output "monthly_cost_estimate" {
  description = "Estimated monthly cost when NAT Gateway is active"
  value       = "~$36/month ($32 NAT Gateway + $3.65 Elastic IP)"
}
