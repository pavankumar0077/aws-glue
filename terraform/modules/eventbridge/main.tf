# terraform/modules/eventbridge/main.tf
# Custom Event Bus
resource "aws_cloudwatch_event_bus" "main" {
  name = "${var.project_name}-event-bus-${var.environment}"
}

# EventBridge Rule for S3 Events
resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name           = "${var.project_name}-s3-object-created-${var.environment}"
  description    = "Trigger Glue job when new data arrives in S3"
  event_bus_name = aws_cloudwatch_event_bus.main.name

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.s3_bucket_raw]
      }
    }
  })
}

# EventBridge Rule for Glue Job State Changes
resource "aws_cloudwatch_event_rule" "glue_job_state_change" {
  name           = "${var.project_name}-glue-job-state-change-${var.environment}"
  description    = "Capture Glue job state changes"
  event_bus_name = aws_cloudwatch_event_bus.main.name

  event_pattern = jsonencode({
    source      = ["aws.glue"]
    detail-type = ["Glue Job State Change"]
    detail = {
      jobName = [for job in var.glue_jobs : job.name]
    }
  })
}

# EventBridge Rule for scheduled execution
resource "aws_cloudwatch_event_rule" "daily_etl_schedule" {
  name                = "${var.project_name}-daily-etl-schedule-${var.environment}"
  description         = "Daily ETL execution schedule"
  schedule_expression = "cron(0 6 * * ? *)"  # 6 AM UTC daily
}

# Lambda targets
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule           = aws_cloudwatch_event_rule.s3_object_created.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "GlueOrchestratorTarget"
  arn            = var.lambda_orchestrator_arn
}

resource "aws_cloudwatch_event_target" "schedule_target" {
  rule      = aws_cloudwatch_event_rule.daily_etl_schedule.name
  target_id = "DailyETLTarget"
  arn       = var.lambda_orchestrator_arn
}

# SNS targets for notifications
resource "aws_cloudwatch_event_target" "sns_target" {
  rule           = aws_cloudwatch_event_rule.glue_job_state_change.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "SNSNotificationTarget"
  arn            = var.sns_topic_arn
}