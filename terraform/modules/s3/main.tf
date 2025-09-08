# terraform/modules/s3/main.tf
resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_name}-raw-data-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "processed_data" {
  bucket = "${var.project_name}-processed-data-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "scripts" {
  bucket = "${var.project_name}-glue-scripts-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "temp" {
  bucket = "${var.project_name}-glue-temp-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Versioning
resource "aws_s3_bucket_versioning" "raw_data_versioning" {
  bucket = aws_s3_bucket.raw_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "processed_data_versioning" {
  bucket = aws_s3_bucket.processed_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policies
resource "aws_s3_bucket_lifecycle_configuration" "raw_data_lifecycle" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    id     = "raw_data_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

# Event notifications
resource "aws_s3_bucket_notification" "raw_data_notification" {
  bucket      = aws_s3_bucket.raw_data.id
  eventbridge = true
}