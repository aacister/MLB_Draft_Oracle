# Your AWS region for App Runner 
aws_region = "us-east-2"

# Your OpenAI API key (get from https://platform.openai.com/api-keys)
# Set via environment variable: export TF_VAR_openai_api_key="your-key-here"
# Or pass via command line: terraform apply -var="openai_api_key=your-key-here"
openai_api_key = ""

# API endpoint from Part 3 (get from Terraform output or API Gateway console)
mlbdraftoracle_api_endpoint = "https://p15b8kyn61.execute-api.us-east-2.amazonaws.com/prod/ingest"

# API key from Part 3 (get from API Gateway console)
# Set via environment variable: export TF_VAR_mlbdraftoracle_api_key="your-key-here"
# Or pass via command line: terraform apply -var="mlbdraftoracle_api_key=your-key-here"
mlbdraftoracle_api_key = ""

# Enable automated research scheduler (optional, default is false)
scheduler_enabled = false