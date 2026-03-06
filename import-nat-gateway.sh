#!/bin/bash
# Import existing NAT Gateway infrastructure into Terraform
# Run this script ONCE to import existing resources

set -e

echo "==========================================="
echo "Importing MLB Draft Oracle NAT Gateway"
echo "Region: us-east-2"
echo "==========================================="
echo ""

# Initialize Terraform
echo "Step 1: Initializing Terraform..."
terraform init
echo "✓ Terraform initialized"
echo ""

# Import Elastic IP
echo "Step 2: Importing Elastic IP..."
terraform import aws_eip.nat eipalloc-03d72ada496441a40
echo "✓ Elastic IP imported"
echo ""

# Import NAT Gateway
echo "Step 3: Importing NAT Gateway..."
terraform import aws_nat_gateway.main nat-0e4a234a1f9a9bb6e
echo "✓ NAT Gateway imported"
echo ""

# Import Routes
echo "Step 4: Importing Routes..."

# Private subnet 2a route
terraform import aws_route.private_2a_nat rtb-0331fd9cd8bf16851_0.0.0.0/0
echo "✓ Private 2a route imported"

# Private subnet 2b route
terraform import aws_route.private_2b_nat rtb-028fbce08449a8eb3_0.0.0.0/0
echo "✓ Private 2b route imported"

# Main route table route
terraform import aws_route.main_nat rtb-0b8d930671e09f679_0.0.0.0/0
echo "✓ Main route table route imported"

echo ""
echo "==========================================="
echo "Import Complete!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "1. Run 'terraform plan' to verify everything matches"
echo "2. If plan shows no changes, you're ready to go!"
echo "3. Use 'terraform destroy' to delete NAT Gateway when needed"
echo "==========================================="
