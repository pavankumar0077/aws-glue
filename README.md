```
2. Upload Glue Scripts to S3
bash# Create temporary S3 bucket for scripts (will be replaced by Terraform)
aws s3 mb s3://temp-glue-scripts-$(date +%s)

# Upload Glue scripts
aws s3 cp glue-scripts/ s3://temp-glue-scripts/scripts/ --recursive

# Update script locations in Terraform configuration
3. Package Lambda Functions
bashcd lambda-functions

# Package orchestrator function
zip -r glue_orchestrator.zip glue_orchestrator.py

# Package validation function
zip -r data_validation.zip data_validation.py

# Move to terraform directory
mv *.zip ../terraform/
cd ../terraform
4. Initialize and Deploy Terraform
bash# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -var-file="terraform.tfvars"

# Apply the configuration
terraform apply -var-file="terraform.tfvars" -auto-approve

5. Upload Updated Scripts
bash# Get the actual S3 bucket name from Terraform output
SCRIPTS_BUCKET=$(terraform output -raw scripts_bucket_name)

# Upload Glue scripts to the correct bucket
aws s3 cp ../glue-scripts/ s3://$SCRIPTS_BUCKET/ --recursive
6. Test the Pipeline
bash# Get bucket names from Terraform output
RAW_BUCKET=$(terraform output -raw raw_data_bucket_name)

# Upload sample data to trigger the pipeline
aws s3 cp sample-data/customers.csv s3://$RAW_BUCKET/customers/
aws s3 cp sample-data/sales.csv s3://$RAW_BUCKET/sales/

# Monitor the pipeline execution
aws glue get-job-runs --job-name $(terraform output -raw customer_etl_job_name)

```
Sample Data Files
customers.csv
csvcustomer_id,first_name,last_name,email,phone,age,city,state,registration_date
1,John,Doe,john.doe@email.com,123-456-7890,32,New York,NY,2023-01-15
2,Jane,Smith,jane.smith@email.com,234-567-8901,28,Los Angeles,CA,2023-02-20
3,Mike,Johnson,mike.johnson@email.com,345-678-9012,45,Chicago,IL,2022-12-10
4,Sarah,Williams,sarah.williams@email.com,456-789-0123,35,Houston,TX,2023-03-05
5,David,Brown,david.brown@email.com,567-890-1234,29,Phoenix,AZ,2023-01-30
```
```
sales.csv
csvsale_id,customer_id,product_id,product_name,amount,sale_date
1,1,101,Laptop,1200.00,2024-01-15
2,1,102,Mouse,25.00,2024-01-16
3,2,103,Keyboard,75.00,2024-01-17
4,3,101,Laptop,1200.00,2024-01-18
5,2,104,Monitor,300.00,2024-01-19
6,4,105,Tablet,500.00,2024-01-20
7,5,106,Phone,800.00,2024-01-21
8,1,107,Headphones,150.00,2024-01-22



```
