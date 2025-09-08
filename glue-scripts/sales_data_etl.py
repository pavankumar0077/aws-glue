# glue-scripts/sales_data_etl.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
import boto3
import json
from datetime import datetime

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'raw_data_bucket',
    'processed_data_bucket',
    'database_name'
])

# Initialize contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Initialize AWS services
eventbridge = boto3.client('events')
s3 = boto3.client('s3')

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

def calculate_business_metrics(df):
    """Calculate business metrics from sales data"""
    # Window specifications
    monthly_window = Window.partitionBy("customer_id", "sales_month")
    yearly_window = Window.partitionBy("customer_id", "sales_year")
    
    # Calculate metrics
    metrics_df = df \
        .withColumn("monthly_total", F.sum("amount").over(monthly_window)) \
        .withColumn("yearly_total", F.sum("amount").over(yearly_window)) \
        .withColumn("avg_order_value", F.avg("amount").over(monthly_window)) \
        .withColumn("order_rank_in_month", F.row_number().over(
            Window.partitionBy("customer_id", "sales_month").orderBy(F.desc("amount"))
        )) \
        .withColumn("running_total", F.sum("amount").over(
            Window.partitionBy("customer_id").orderBy("sale_date")
            .rangeBetween(Window.unboundedPreceding, Window.currentRow)
        ))
    
    return metrics_df

try:
    print("Starting Sales Data ETL Job...")
    
    # Read raw sales data
    sales_data_path = f"s3://{args['raw_data_bucket']}/sales/"
    
    sales_dynamic_frame = glueContext.create_dynamic_frame.from_options(
        format_options={"quoteChar": "\"", "withHeader": True, "separator": ","},
        connection_type="s3",
        format="csv",
        connection_options={
            "paths": [sales_data_path],
            "recurse": True
        },
        transformation_ctx="sales_dynamic_frame"
    )
    
    print(f"Raw sales records count: {sales_dynamic_frame.count()}")
    
    # Convert to DataFrame
    sales_df = sales_dynamic_frame.toDF()
    
    # Data validation
    total_records = sales_df.count()
    null_customer_ids = sales_df.filter(F.col("customer_id").isNull()).count()
    invalid_amounts = sales_df.filter(F.col("amount") <= 0).count()
    
    # Data transformations
    sales_transformed_df = sales_df \
        .filter(F.col("customer_id").isNotNull()) \
        .filter(F.col("amount") > 0) \
        .withColumn("sale_date", F.to_date(F.col("sale_date"), "yyyy-MM-dd")) \
        .withColumn("sales_year", F.year(F.col("sale_date"))) \
        .withColumn("sales_month", F.month(F.col("sale_date"))) \
        .withColumn("sales_quarter", F.quarter(F.col("sale_date"))) \
        .withColumn("day_of_week", F.dayofweek(F.col("sale_date"))) \
        .withColumn("is_weekend", F.when(F.col("day_of_week").isin([1, 7]), True).otherwise(False)) \
        .withColumn("amount_category", 
                   F.when(F.col("amount") < 100, "Small")
                    .when(F.col("amount") < 500, "Medium")
                    .when(F.col("amount") < 1000, "Large")
                    .otherwise("Very Large")) \
        .withColumn("processed_timestamp", F.current_timestamp()) \
        .withColumn("data_source", F.lit("sales_system")) \
        .withColumn("etl_job_name", F.lit(args['JOB_NAME']))
    
    # Calculate business metrics
    sales_with_metrics_df = calculate_business_metrics(sales_transformed_df)
    
    # Add customer segmentation based on purchase behavior
    customer_segments_df = sales_with_metrics_df \
        .groupBy("customer_id") \
        .agg(
            F.sum("amount").alias("total_spent"),
            F.count("sale_id").alias("total_orders"),
            F.avg("amount").alias("avg_order_value"),
            F.max("sale_date").alias("last_purchase_date"),
            F.min("sale_date").alias("first_purchase_date")
        ) \
        .withColumn("customer_lifetime_days", 
                   F.datediff(F.col("last_purchase_date"), F.col("first_purchase_date"))) \
        .withColumn("customer_segment",
                   F.when((F.col("total_spent") > 5000) & (F.col("total_orders") > 10), "VIP")
                    .when((F.col("total_spent") > 1000) & (F.col("total_orders") > 5), "High Value")
                    .when(F.col("total_orders") > 3, "Regular")
                    .otherwise("New"))
    
    # Join back with main sales data
    sales_final_df = sales_with_metrics_df.join(
        customer_segments_df.select("customer_id", "customer_segment", "total_spent", "total_orders"),
        "customer_id",
        "left"
    )
    
    print(f"Transformed sales records count: {sales_final_df.count()}")
    
    # Convert back to Dynamic Frame
    sales_final_dynamic_frame = DynamicFrame.fromDF(
        sales_final_df, 
        glueContext, 
        "sales_final_dynamic_frame"
    )
    
    # Write partitioned data to S3
    output_path = f"s3://{args['processed_data_bucket']}/sales/"
    
    glueContext.write_dynamic_frame.from_options(
        frame=sales_final_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": output_path,
            "partitionKeys": ["sales_year", "sales_month"]
        },
        format="glueparquet",
        transformation_ctx="write_sales_data"
    )
    
    # Write customer segments separately
    customer_segments_output_path = f"s3://{args['processed_data_bucket']}/customer_segments/"
    customer_segments_dynamic_frame = DynamicFrame.fromDF(
        customer_segments_df,
        glueContext,
        "customer_segments_dynamic_frame"
    )
    
    glueContext.write_dynamic_frame.from_options(
        frame=customer_segments_dynamic_frame,
        connection_type="s3",
        connection_options={"path": customer_segments_output_path},
        format="glueparquet",
        transformation_ctx="write_customer_segments"
    )
    
    # Update Data Catalog
    glueContext.write_dynamic_frame.from_catalog(
        frame=sales_final_dynamic_frame,
        database=args['database_name'],
        table_name="processed_sales",
        transformation_ctx="catalog_write_sales_data"
    )
    
    # Send success metrics
    success_details = {
        'job_name': args['JOB_NAME'],
        'status': 'SUCCESS',
        'records_processed': sales_final_df.count(),
        'data_quality': {
            'total_records': total_records,
            'null_customer_ids': null_customer_ids,
            'invalid_amounts': invalid_amounts,
            'valid_records_percentage': ((total_records - null_customer_ids - invalid_amounts) / total_records) * 100
        },
        'customer_segments': {
            segment_row['customer_segment']: segment_row['count'] 
            for segment_row in customer_segments_df.groupBy("customer_segment").count().collect()
        },
        'output_path': output_path,
        'completion_time': datetime.now().isoformat()
    }
    
    send_custom_event("ETL Job Completed", success_details)
    
    print(f"Sales ETL job completed successfully. Records processed: {sales_final_df.count()}")
    
except Exception as e:
    print(f"Error in Sales ETL job: {str(e)}")
    
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