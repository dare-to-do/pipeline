import json
import boto3
import os

sqs_client = boto3.client('sqs')
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']


def send_to_sqs(message):
    try:
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        print(f"Message sent to SQS: {response['MessageId']}")
        return {
            'status_code': 200,
            'body': json.dumps('Messages sent to SQS successfully!')
        }
    except Exception as e:
        print(f"Error sending message to SQS: {str(e)}")
        return {
            'status_code': 500,
            'body': json.dumps('Error sending messages to SQS!')
        }


def lambda_handler(event, context):
    bucket_name = event['bucket_name']
    file_name = event['file_name']

    # 메시지 생성
    message = {
        'bucket_name': bucket_name,
        'file_name': file_name
    }

    return send_to_sqs(message)
