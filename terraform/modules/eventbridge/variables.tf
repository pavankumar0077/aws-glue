variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, prod, etc.)"
  type        = string
}

variable "s3_bucket_raw" {
  description = "Raw data S3 bucket name"
  type        = string
}

variable "glue_jobs" {
  description = "List of Glue jobs"
  type        = list(object({
    name = string
  }))
}

variable "lambda_orchestrator_arn" {
  description = "ARN of the Lambda orchestrator function"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  type        = string
}