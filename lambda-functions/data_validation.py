import json

def lambda_handler(event, context):
    # Validate incoming S3 event structure
    records = event.get('Records', [])
    validation_results = []

    for record in records:
        s3_info = record.get('s3', {})
        bucket = s3_info.get('bucket', {}).get('name')
        key = s3_info.get('object', {}).get('key')

        # Example validation: Check file extension
        if key and key.endswith('.csv'):
            result = f"File {key} in bucket {bucket} is valid."
        else:
            result = f"File {key} in bucket {bucket} is invalid or missing."

        validation_results.append(result)

    print("Validation Results:", validation_results)
    return {
        "status": "Validation complete",
        "results": validation_results
    }