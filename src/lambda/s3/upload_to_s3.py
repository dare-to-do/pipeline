import boto3
import json
from datetime import datetime, timezone, timedelta

utc_now = datetime.now(timezone.utc)
seoul_timezone = timezone(timedelta(hours=9))
seoul_now = utc_now.astimezone(seoul_timezone)


def upload_to_s3(bucket_name, file_name, file_content):
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
        return {
            'status_code': 200,
            'bucket_name': bucket_name,
            'file_name': file_name
        }
    except Exception as e:
        return {
            'status_code': 500,
            'body': str(e)
        }


def lambda_handler(event, context):
    bucket_name = 'bucket-for-scraping-lambda'
    now = seoul_now.strftime("%Y/%m/%d/%H")

    site_name = event['from']
    file_name = site_name + '/' + now + '.json'
    image_name = site_name + '/' + now + '.png'

    content = event['body']

    return upload_to_s3(bucket_name, file_name, bytes(json.dumps(content).encode('utf-8')))
