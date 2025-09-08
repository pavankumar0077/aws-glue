output "raw_data_bucket" {
  description = "Raw data S3 bucket name"
  value       = aws_s3_bucket.raw_data.bucket
}

output "processed_data_bucket" {
  description = "Processed data S3 bucket name"
  value       = aws_s3_bucket.processed_data.bucket
}

output "scripts_bucket" {
  description = "Glue scripts S3 bucket name"
  value       = aws_s3_bucket.scripts.bucket
}

output "temp_bucket" {
  description = "Glue temp S3 bucket name"
  value       = aws_s3_bucket.temp.bucket
}