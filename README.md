``` mermaid
graph TB
    subgraph "Data Sources"
        DS1[Customer Data Files]
        DS2[Sales Data Files]
        DS3[External APIs]
    end
    
    subgraph "AWS S3 Data Lake"
        S3Raw[S3 Raw Data Bucket<br/>Raw CSV/JSON files]
        S3Processed[S3 Processed Data Bucket<br/>Parquet files partitioned]
        S3Scripts[S3 Scripts Bucket<br/>Glue ETL scripts]
        S3Temp[S3 Temp Bucket<br/>Temporary processing files]
    end
    
    subgraph "AWS Glue"
        GlueCrawler[Glue Crawler<br/>Schema Discovery]
        GlueDB[(Glue Data Catalog<br/>Metadata Repository)]
        
        subgraph "ETL Jobs"
            Job1[Customer Data ETL<br/>- Data validation<br/>- Transformation<br/>- Quality checks]
            Job2[Sales Data ETL<br/>- Business metrics<br/>- Customer segmentation<br/>- Aggregations]
            Job3[Data Quality Job<br/>- Validation rules<br/>- Quality scoring<br/>- Report generation]
        end
        
        GlueWorkflow[Glue Workflow<br/>Job orchestration]
    end
    
    subgraph "AWS EventBridge"
        EventBus[Custom Event Bus]
        
        subgraph "Event Rules"
            Rule1[S3 Object Created Rule]
            Rule2[Glue Job State Change Rule]
            Rule3[Scheduled ETL Rule]
            Rule4[Quality Check Rule]
        end
    end
    
    subgraph "AWS Lambda"
        Lambda1[Glue Job Orchestrator<br/>- Job triggering<br/>- State management<br/>- Error handling]
        Lambda2[Data Validation<br/>- Custom validations<br/>- Business rules]
    end
    
    subgraph "Monitoring & Notifications"
        CW[CloudWatch<br/>Metrics & Logs]
        SNS[SNS Topic<br/>Notifications]
        Email[Email Notifications]
    end
    
    subgraph "Analytics & BI"
        Athena[Amazon Athena<br/>SQL Analytics]
        QuickSight[Amazon QuickSight<br/>Dashboards]
        BI[External BI Tools<br/>Tableau, PowerBI]
    end
    
    %% Data Flow
    DS1 --> S3Raw
    DS2 --> S3Raw
    DS3 --> S3Raw
    
    S3Raw -->|File arrival event| Rule1
    Rule1 --> Lambda1
    Lambda1 --> Job1
    Lambda1 --> Job2
    
    Job1 -->|Process customer data| S3Processed
    Job2 -->|Process sales data| S3Processed
    
    Job1 -->|State change| Rule2
    Job2 -->|State change| Rule2
    Rule2 --> Lambda1
    
    Lambda1 -->|Trigger quality job| Job3
    Job3 --> S3Processed
    
    Rule3 -->|Daily schedule| Lambda1
    GlueCrawler --> GlueDB
    S3Raw --> GlueCrawler
    S3Processed --> GlueCrawler
    
    Job1 --> CW
    Job2 --> CW
    Job3 --> CW
    Lambda1 --> CW
    
    Rule2 --> SNS
    SNS --> Email
    
    S3Processed --> Athena
    Athena --> QuickSight
    S3Processed --> BI
    
    EventBus --> Rule1
    EventBus --> Rule2
    EventBus --> Rule3
    EventBus --> Rule4
    
    %% Styling
    classDef awsService fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white
    classDef dataStore fill:#3F48CC,stroke:#232F3E,stroke-width:2px,color:white
    classDef etlJob fill:#7AA116,stroke:#232F3E,stroke-width:2px,color:white
    classDef eventService fill:#FF4B4B,stroke:#232F3E,stroke-width:2px,color:white
    
    class S3Raw,S3Processed,S3Scripts,S3Temp dataStore
    class Job1,Job2,Job3 etlJob
    class EventBus,Rule1,Rule2,Rule3,Rule4 eventService
    class Lambda1,Lambda2,CW,SNS,Athena,QuickSight awsService
```

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
