# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "terraform-state-glue-eventbridge"
    key    = "glue-eventbridge/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "AWS-Glue-EventBridge"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data Sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# S3 Module
module "s3" {
  source = "./modules/s3"
  
  environment = var.environment
  project_name = var.project_name
}

# Glue Module
module "glue" {
  source = "./modules/glue"
  
  environment = var.environment
  project_name = var.project_name
  s3_bucket_raw = module.s3.raw_data_bucket
  s3_bucket_processed = module.s3.processed_data_bucket
  s3_bucket_scripts = module.s3.scripts_bucket
}

# EventBridge Module
module "eventbridge" {
  source = "./modules/eventbridge"
  
  environment = var.environment
  project_name = var.project_name
  glue_jobs = module.glue.glue_jobs
}

# Lambda for orchestration
resource "aws_lambda_function" "glue_orchestrator" {
  filename         = "glue_orchestrator.zip"
  function_name    = "${var.project_name}-glue-orchestrator-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "glue_orchestrator.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  
  environment {
    variables = {
      GLUE_JOB_NAMES = jsonencode(module.glue.glue_job_names)
      EVENT_BUS_NAME = module.eventbridge.event_bus_name
    }
  }
}

# SNS for notifications
resource "aws_sns_topic" "glue_notifications" {
  name = "${var.project_name}-glue-notifications-${var.environment}"
}

resource "aws_sns_topic_subscription" "email_notification" {
  topic_arn = aws_sns_topic.glue_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}