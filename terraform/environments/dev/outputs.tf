output "eventbridge_event_bus_name" {
  description = "Name of the EventBridge event bus"
  value       = module.eventbridge.event_bus_name
}

output "eventbridge_s3_object_created_rule_arn" {
  description = "ARN of the S3 Object Created EventBridge rule"
  value       = module.eventbridge.s3_object_created_rule_arn
}

output "eventbridge_glue_job_state_change_rule_arn" {
  description = "ARN of the Glue Job State Change EventBridge rule"
  value       = module.eventbridge.glue_job_state_change_rule_arn
}

output "glue_job_names" {
  description = "Names of Glue jobs"
  value       = module.glue.glue_job_names
}

output "glue_main_workflow_name" {
  description = "Name of the Glue workflow"
  value       = module.glue.main_workflow_name
}

output "s3_raw_data_bucket" {
  description = "Raw data S3 bucket name"
  value       = module.s3.raw_data_bucket
}

output "s3_processed_data_bucket" {
  description = "Processed data S3 bucket name"
  value       = module.s3.processed_data_bucket
}

output "s3_scripts_bucket" {
  description = "Glue scripts S3 bucket name"
  value       = module.s3.scripts_bucket
}

output "s3_temp_bucket" {
  description = "Glue temp S3 bucket name"
  value       = module.s3.temp_bucket
}