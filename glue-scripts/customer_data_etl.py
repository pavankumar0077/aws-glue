# glue-scripts/customer_data_etl.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *
import boto3
from datetime import datetime

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'raw_data_bucket',
    'processed_data_bucket',
    'database_name'
])

# Initialize Spark and Glue contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Initialize EventBridge client for custom events
eventbridge = boto3.client('events')

def send_custom_event(event_type, details):
    """Send custom event to EventBridge"""
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'custom.glue.etl',
                    'DetailType': event_type,
                    'Detail': json.dumps(details)
                }
            ]
        )
    except Exception as e:
        print(f"Failed to send event: {str(e)}")

def validate_data_quality(df, job_name):
    """Validate data quality and return metrics"""
    total_records = df.count()
    null_records = df.filter(F.col("customer_id").isNull()).count()
    duplicate_records = df.count() - df.dropDuplicates(["customer_id"]).count()
    
    quality_metrics = {
        'job_name': job_name,
        'total_records': total_records,
        'null_records': null_records,
        'duplicate_records': duplicate_records,
        'null_percentage': (null_records / total_records) * 100 if total_records > 0 else 0,
        'duplicate_percentage': (duplicate_records / total_records) * 100 if total_records > 0 else 0
    }
    
    return quality_metrics

try:
    print("Starting Customer Data ETL Job...")
    
    # Read raw customer data from S3
    customer_data_path = f"s3://{args['raw_data_bucket']}/customers/"
    
    # Create dynamic frame from S3
    customer_dynamic_frame = glueContext.create_dynamic_frame.from_options(
        format_options={"quoteChar": "\"", "withHeader": True, "separator": ","},
        connection_type="s3",
        format="csv",
        connection_options={
            "paths": [customer_data_path],
            "recurse": True
        },
        transformation_ctx="customer_dynamic_frame"
    )
    
    print(f"Raw records count: {customer_dynamic_frame.count()}")
    
    # Convert to Spark DataFrame for complex transformations
    customer_df = customer_dynamic_frame.toDF()
    
    # Data validation and quality checks
    quality_metrics = validate_data_quality(customer_df, args['JOB_NAME'])
    print(f"Data Quality Metrics: {quality_metrics}")
    
    # Send quality metrics event
    send_custom_event("Data Quality Check", quality_metrics)
    
    # Data transformations
    customer_transformed_df = customer_df \
        .filter(F.col("customer_id").isNotNull()) \
        .dropDuplicates(["customer_id"]) \
        .withColumn("full_name", F.concat_ws(" ", F.col("first_name"), F.col("last_name"))) \
        .withColumn("email_domain", F.regexp_extract(F.col("email"), "@(.+)", 1)) \
        .withColumn("age_group", 
                   F.when(F.col("age") < 25, "Young")
                    .when(F.col("age") < 45, "Adult")
                    .when(F.col("age") < 65, "Middle-aged")
                    .otherwise("Senior")) \
        .withColumn("registration_year", F.year(F.col("registration_date"))) \
        .withColumn("processed_timestamp", F.current_timestamp()) \
        .withColumn("data_source", F.lit("customer_system")) \
        .withColumn("etl_job_name", F.lit(args['JOB_NAME']))
    
    # Add data lineage information
    customer_transformed_df = customer_transformed_df.withColumn(
        "data_lineage", 
        F.struct(
            F.lit("customer_data_etl").alias("job_name"),
            F.current_timestamp().alias("processed_at"),
            F.lit(customer_data_path).alias("source_path")
        )
    )
    
    print(f"Transformed records count: {customer_transformed_df.count()}")
    
    # Convert back to Dynamic Frame
    customer_transformed_dynamic_frame = DynamicFrame.fromDF(
        customer_transformed_df, 
        glueContext, 
        "customer_transformed_dynamic_frame"
    )
    
    # Apply additional Glue transformations
    customer_final_dynamic_frame = ApplyMapping.apply(
        frame=customer_transformed_dynamic_frame,
        mappings=[
            ("customer_id", "string", "customer_id", "string"),
            ("full_name", "string", "full_name", "string"),
            ("email", "string", "email", "string"),
            ("email_domain", "string", "email_domain", "string"),
            ("phone", "string", "phone", "string"),
            ("age", "int", "age", "int"),
            ("age_group", "string", "age_group", "string"),
            ("city", "string", "city", "string"),
            ("state", "string", "state", "string"),
            ("registration_year", "int", "registration_year", "int"),
            ("processed_timestamp", "timestamp", "processed_timestamp", "timestamp"),
            ("data_source", "string", "data_source", "string"),
            ("etl_job_name", "string", "etl_job_name", "string")
        ]
    )
    
    # Write to S3 in Parquet format partitioned by registration_year
    output_path = f"s3://{args['processed_data_bucket']}/customers/"
    
    glueContext.write_dynamic_frame.from_options(
        frame=customer_final_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": output_path,
            "partitionKeys": ["registration_year"]
        },
        format="glueparquet",
        transformation_ctx="write_customer_data"
    )
    
    # Update Glue Data Catalog
    glueContext.write_dynamic_frame.from_catalog(
        frame=customer_final_dynamic_frame,
        database=args['database_name'],
        table_name="processed_customers",
        transformation_ctx="catalog_write_customer_data"
    )
    
    # Send success event
    success_details = {
        'job_name': args['JOB_NAME'],
        'status': 'SUCCESS',
        'records_processed': customer_transformed_df.count(),
        'output_path': output_path,
        'completion_time': datetime.now().isoformat()
    }
    
    send_custom_event("ETL Job Completed", success_details)
    
    print(f"Customer ETL job completed successfully. Records processed: {customer_transformed_df.count()}")
    
except Exception as e:
    print(f"Error in Customer ETL job: {str(e)}")
    
    # Send failure event
    failure_details = {
        'job_name': args['JOB_NAME'],
        'status': 'FAILED',
        'error_message': str(e),
        'failure_time': datetime.now().isoformat()
    }
    
    send_custom_event("ETL Job Failed", failure_details)
    
    raise e

finally:
    job.commit()