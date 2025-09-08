# terraform/variables.tf
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "data-pipeline"
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
}

variable "glue_job_timeout" {
  description = "Timeout for Glue jobs in minutes"
  type        = number
  default     = 60
}

variable "glue_worker_type" {
  description = "Glue worker type"
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of workers for Glue jobs"
  type        = number
  default     = 2
}

variable "enable_glue_job_insights" {
  description = "Enable Glue job insights"
  type        = bool
  default     = true
}

variable "s3_lifecycle_transition_days" {
  description = "Days before transitioning to IA storage"
  type        = number
  default     = 30
}

variable "eventbridge_schedule_expression" {
  description = "Schedule expression for EventBridge rule"
  type        = string
  default     = "cron(0 6 * * ? *)"
}