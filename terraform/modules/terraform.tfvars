# terraform/terraform.tfvars
aws_region = "us-east-1"
environment = "dev"
project_name = "enterprise-data-pipeline"
notification_email = "data-team@company.com"
glue_job_timeout = 90
glue_worker_type = "G.2X"
glue_number_of_workers = 3
enable_glue_job_insights = true
s3_lifecycle_transition_days = 30
