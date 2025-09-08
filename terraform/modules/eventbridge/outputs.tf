output "event_bus_name" {
  description = "Name of the EventBridge event bus"
  value       = aws_cloudwatch_event_bus.main.name
}

output "s3_object_created_rule_arn" {
  description = "ARN of the S3 Object Created EventBridge rule"
  value       = aws_cloudwatch_event_rule.s3_object_created.arn
}

output "glue_job_state_change_rule_arn" {
  description = "ARN of the Glue Job State Change EventBridge rule"
  value       = aws_cloudwatch_event_rule.glue_job_state_change.arn
}