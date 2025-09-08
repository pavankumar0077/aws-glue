# lambda-functions/glue_job_orchestrator.py
import json
import boto3
import os
from datetime import datetime

glue = boto3.client('glue')
eventbridge = boto3.client('events')

def lambda_handler(event, context):
    """
    Orchestrate Glue jobs based on EventBridge events
    """
    
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Parse the event
        event_source = event.get('source', '')
        event_detail_type = event.get('detail-type', '')
        event_detail = event.get('detail', {})
        
        response = {
            'statusCode': 200,
            'orchestration_results': []
        }
        
        # Handle S3 object created events
        if event_source == 'aws.s3' and event_detail_type == 'Object Created':
            bucket_name = event_detail.get('bucket', {}).get('name', '')
            object_key = event_detail.get('object', {}).get('key', '')
            
            print(f"Processing S3 event: {bucket_name}/{object_key}")
            
            # Determine which ETL jobs to trigger based on object path
            jobs_to_trigger = []
            
            if 'customers/' in object_key:
                jobs_to_trigger.append('customer-data-etl')
            elif 'sales/' in object_key:
                jobs_to_trigger.append('sales-data-etl')
            
            # Trigger appropriate Glue jobs
            for job_name in jobs_to_trigger:
                full_job_name = f"{os.environ.get('PROJECT_NAME', 'data-pipeline')}-{job_name}-{os.environ.get('ENVIRONMENT', 'dev')}"
                
                job_run_response = start_glue_job(full_job_name, {
                    'trigger_event': 'S3_OBJECT_CREATED',
                    'source_bucket': bucket_name,
                    'source_key': object_key
                })
                
                response['orchestration_results'].append({
                    'job_name': full_job_name,
                    'job_run_id': job_run_response.get('JobRunId'),
                    'status': 'STARTED'
                })
        
        # Handle scheduled events
        elif event_source == 'aws.events' and 'Scheduled Event' in event.get('resources', [''])[0]:
            print("Processing scheduled event")
            
            # Start the main workflow
            workflow_name = f"{os.environ.get('PROJECT_NAME', 'data-pipeline')}-main-workflow-{os.environ.get('ENVIRONMENT', 'dev')}"
            
            try:
                workflow_response = glue.start_workflow_run(Name=workflow_name)
                
                response['orchestration_results'].append({
                    'workflow_name': workflow_name,
                    'workflow_run_id': workflow_response.get('RunId'),
                    'status': 'STARTED'
                })
                
            except Exception as workflow_error:
                print(f"Failed to start workflow: {str(workflow_error)}")
                response['orchestration_results'].append({
                    'workflow_name': workflow_name,
                    'status': 'FAILED',
                    'error': str(workflow_error)
                })
        
        # Handle Glue job state changes
        elif event_source == 'aws.glue' and event_detail_type == 'Glue Job State Change':
            job_name = event_detail.get('jobName', '')
            job_run_id = event_detail.get('jobRunId', '')
            job_state = event_detail.get('state', '')
            
            print(f"Glue job {job_name} changed state to {job_state}")
            
            # Handle job completion logic
            if job_state == 'SUCCEEDED':
                handle_job_success(job_name, job_run_id, event_detail)
            elif job_state == 'FAILED':
                handle_job_failure(job_name, job_run_id, event_detail)
            
            response['orchestration_results'].append({
                'job_name': job_name,
                'job_run_id': job_run_id,
                'state': job_state,
                'processed': True
            })
        
        # Send orchestration completion event
        send_orchestration_event({
            'orchestration_timestamp': datetime.now().isoformat(),
            'event_processed': event_detail_type,
            'results': response['orchestration_results']
        })
        
        return response
        
    except Exception as e:
        print(f"Error in orchestration: {str(e)}")
        
        # Send failure event
        send_orchestration_event({
            'orchestration_timestamp': datetime.now().isoformat(),
            'status': 'FAILED',
            'error': str(e),
            'original_event': event
        })
        
        return {
            'statusCode': 500,
            'error': str(e)
        }

def start_glue_job(job_name, arguments=None):
    """Start a Glue job with optional arguments"""
    try:
        job_args = arguments or {}
        
        response = glue.start_job_run(
            JobName=job_name,
            Arguments={f'--{k}': v for k, v in job_args.items()}
        )
        
        print(f"Started Glue job {job_name} with run ID: {response['JobRunId']}")
        return response
        
    except Exception as e:
        print(f"Failed to start Glue job {job_name}: {str(e)}")
        raise e

def handle_job_success(job_name, job_run_id, job_details):
    """Handle successful job completion"""
    print(f"Job {job_name} completed successfully")
    
    # Get job run details
    try:
        job_run_details = glue.get_job_run(JobName=job_name, RunId=job_run_id)
        execution_time = job_run_details['JobRun'].get('ExecutionTime', 0)
        
        # Trigger downstream jobs if needed
        if 'customer-data-etl' in job_name or 'sales-data-etl' in job_name:
            # Check if both customer and sales ETL jobs are complete
            check_and_trigger_quality_job()
        
        # Send success metrics
        send_job_metrics({
            'job_name': job_name,
            'job_run_id': job_run_id,
            'status': 'SUCCESS',
            'execution_time_seconds': execution_time,
            'completion_timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error handling job success for {job_name}: {str(e)}")

def handle_job_failure(job_name, job_run_id, job_details):
    """Handle job failure"""
    print(f"Job {job_name} failed")
    
    try:
        job_run_details = glue.get_job_run(JobName=job_name, RunId=job_run_id)
        error_message = job_run_details['JobRun'].get('ErrorMessage', 'Unknown error')
        
        # Send failure notification
        send_failure_notification({
            'job_name': job_name,
            'job_run_id': job_run_id,
            'error_message': error_message,
            'failure_timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error handling job failure for {job_name}: {str(e)}")

def check_and_trigger_quality_job():
    """Check if both ETL jobs are complete and trigger quality job"""
    try:
        # This is a simplified check - in production, you'd want to track job states
        quality_job_name = f"{os.environ.get('PROJECT_NAME', 'data-pipeline')}-data-quality-check-{os.environ.get('ENVIRONMENT', 'dev')}"
        
        start_glue_job(quality_job_name, {
            'trigger_reason': 'ETL_JOBS_COMPLETED'
        })
        
    except Exception as e:
        print(f"Failed to trigger quality job: {str(e)}")

def send_orchestration_event(details):
    """Send orchestration event to EventBridge"""
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'custom.lambda.orchestrator',
                    'DetailType': 'Job Orchestration',
                    'Detail': json.dumps(details)
                }
            ]
        )
    except Exception as e:
        print(f"Failed to send orchestration event: {str(e)}")

def send_job_metrics(metrics):
    """Send job metrics to EventBridge"""
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'custom.lambda.metrics',
                    'DetailType': 'Job Metrics',
                    'Detail': json.dumps(metrics)
                }
            ]
        )
    except Exception as e:
        print(f"Failed to send job metrics: {str(e)}")

def send_failure_notification(failure_details):
    """Send failure notification"""
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'custom.lambda.notifications',
                    'DetailType': 'Job Failure Alert',
                    'Detail': json.dumps(failure_details)
                }
            ]
        )
    except Exception as e:
        print(f"Failed to send failure notification: {str(e)}")