# terraform/modules/glue/main.tf
# Glue Database
resource "aws_glue_catalog_database" "main" {
  name = "${var.project_name}_${var.environment}_database"
  
  description = "Main database for ${var.project_name} project"
}

# Glue Crawler for raw data discovery
resource "aws_glue_crawler" "raw_data_crawler" {
  name          = "${var.project_name}-raw-data-crawler-${var.environment}"
  database_name = aws_glue_catalog_database.main.name
  role          = aws_iam_role.glue_role.arn
  
  s3_target {
    path = "s3://${var.s3_bucket_raw}/"
  }
  
  schedule = "cron(0 2 * * ? *)"  # Run daily at 2 AM
  
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DELETE_FROM_DATABASE"
  }
}

# Customer Data ETL Job
resource "aws_glue_job" "customer_data_etl" {
  name          = "${var.project_name}-customer-data-etl-${var.environment}"
  role_arn      = aws_iam_role.glue_role.arn
  glue_version  = "4.0"
  worker_type   = "G.1X"
  number_of_workers = 2
  timeout       = 60
  
  command {
    script_location = "s3://${var.s3_bucket_scripts}/customer_data_etl.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--enable-metrics"                = ""
    "--enable-spark-ui"              = "true"
    "--spark-event-logs-path"        = "s3://${var.s3_bucket_scripts}/sparkHistoryLogs/"
    "--enable-job-insights"          = "true"
    "--enable-observability-metrics" = "true"
    "--job-bookmark-option"          = "job-bookmark-enable"
    "--TempDir"                      = "s3://${var.s3_bucket_scripts}/temp/"
    "--raw_data_bucket"              = var.s3_bucket_raw
    "--processed_data_bucket"        = var.s3_bucket_processed
    "--database_name"                = aws_glue_catalog_database.main.name
  }
}

# Sales Data ETL Job
resource "aws_glue_job" "sales_data_etl" {
  name          = "${var.project_name}-sales-data-etl-${var.environment}"
  role_arn      = aws_iam_role.glue_role.arn
  glue_version  = "4.0"
  worker_type   = "G.1X"
  number_of_workers = 3
  timeout       = 90
  
  command {
    script_location = "s3://${var.s3_bucket_scripts}/sales_data_etl.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--enable-metrics"                = ""
    "--enable-spark-ui"              = "true"
    "--spark-event-logs-path"        = "s3://${var.s3_bucket_scripts}/sparkHistoryLogs/"
    "--enable-job-insights"          = "true"
    "--enable-observability-metrics" = "true"
    "--job-bookmark-option"          = "job-bookmark-enable"
    "--TempDir"                      = "s3://${var.s3_bucket_scripts}/temp/"
    "--raw_data_bucket"              = var.s3_bucket_raw
    "--processed_data_bucket"        = var.s3_bucket_processed
    "--database_name"                = aws_glue_catalog_database.main.name
  }
}

# Data Quality Job
resource "aws_glue_job" "data_quality_check" {
  name          = "${var.project_name}-data-quality-check-${var.environment}"
  role_arn      = aws_iam_role.glue_role.arn
  glue_version  = "4.0"
  worker_type   = "G.1X"
  number_of_workers = 2
  timeout       = 30
  
  command {
    script_location = "s3://${var.s3_bucket_scripts}/data_quality_check.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--enable-metrics"        = ""
    "--processed_data_bucket" = var.s3_bucket_processed
    "--database_name"         = aws_glue_catalog_database.main.name
  }
}

# Glue Workflow
resource "aws_glue_workflow" "main_workflow" {
  name = "${var.project_name}-main-workflow-${var.environment}"
  
  description = "Main ETL workflow for ${var.project_name}"
}

# Workflow triggers
resource "aws_glue_trigger" "workflow_start" {
  name          = "${var.project_name}-workflow-start-${var.environment}"
  type          = "ON_DEMAND"
  workflow_name = aws_glue_workflow.main_workflow.name
  
  actions {
    job_name = aws_glue_job.customer_data_etl.name
  }
  
  actions {
    job_name = aws_glue_job.sales_data_etl.name
  }
}

resource "aws_glue_trigger" "data_quality_trigger" {
  name          = "${var.project_name}-data-quality-trigger-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main_workflow.name
  
  actions {
    job_name = aws_glue_job.data_quality_check.name
  }
  
  predicate {
    conditions {
      job_name = aws_glue_job.customer_data_etl.name
      logical_operator = "EQUALS"
      state = "SUCCEEDED"
    }
    
    conditions {
      job_name = aws_glue_job.sales_data_etl.name
      logical_operator = "EQUALS"
      state = "SUCCEEDED"
    }
  }
}

# IAM Role for Glue
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-glue-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_policy" {
  name = "${var.project_name}-glue-s3-policy-${var.environment}"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_raw}/*",
          "arn:aws:s3:::${var.s3_bucket_processed}/*",
          "arn:aws:s3:::${var.s3_bucket_scripts}/*",
          "arn:aws:s3:::${var.s3_bucket_raw}",
          "arn:aws:s3:::${var.s3_bucket_processed}",
          "arn:aws:s3:::${var.s3_bucket_scripts}"
        ]
      }
    ]
  })
}