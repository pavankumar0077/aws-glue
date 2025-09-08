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

variable "s3_bucket_processed" {
  description = "Processed data S3 bucket name"
  type        = string
}

variable "s3_bucket_scripts" {
  description = "Scripts S3 bucket name"
  type        = string
}