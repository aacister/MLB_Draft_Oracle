variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "mlbdraftoracle_api_endpoint" {
  description = "MLBDRAFTORACLE API endpoint"
  type        = string
}

variable "mlbdraftoracle_api_key" {
  description = "MLBDRAFTORACLE API key"
  type        = string
  sensitive   = true
}

variable "scheduler_enabled" {
  description = "Enable automated research scheduler"
  type        = bool
  default     = false
}