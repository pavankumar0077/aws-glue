output "glue_jobs" {
  description = "List of Glue job objects"
  value = [
    {
      name = aws_glue_job.customer_data_etl.name
    },
    {
      name = aws_glue_job.sales_data_etl.name
    },
    {
      name = aws_glue_job.data_quality_check.name
    }
  ]
}

output "glue_job_names" {
  description = "Names of Glue jobs"
  value = [
    aws_glue_job.customer_data_etl.name,
    aws_glue_job.sales_data_etl.name,
    aws_glue_job.data_quality_check.name
  ]
}

output "main_workflow_name" {
  description = "Name of the Glue workflow"
  value       = aws_glue_workflow.main_workflow.name
}