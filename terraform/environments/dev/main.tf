terraform {
  backend "s3" {
    bucket = "your-terraform-state-dev"
    key    = "aws-glue/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "default"
}

module "s3" {
  source       = "../../modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "glue" {
  source              = "../../modules/glue"
  project_name        = var.project_name
  environment         = var.environment
  s3_bucket_raw       = module.s3.raw_data_bucket
  s3_bucket_processed = module.s3.processed_data_bucket
  s3_bucket_scripts   = module.s3.scripts_bucket
}

module "eventbridge" {
  source                  = "../../modules/eventbridge"
  project_name            = var.project_name
  environment             = var.environment
  s3_bucket_raw           = module.s3.raw_data_bucket
  glue_jobs               = module.glue.glue_jobs
  lambda_orchestrator_arn = var.lambda_orchestrator_arn
  sns_topic_arn           = var.sns_topic_arn
}