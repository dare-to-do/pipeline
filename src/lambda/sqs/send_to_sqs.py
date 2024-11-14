import json
import boto3
import os

sqs_client = boto3.client('sqs')
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']


def lambda_handler(event, context):
    bucket_name = event['bucket_name']
    file_name = event['file_name']

    # 메시지 생성
    message = {
        'bucket_name': bucket_name,
        'file_name': file_name
    }

    try:
        # SQS에 메시지 전송
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        print(f"Message sent to SQS: {response['MessageId']}")

        return {
            'statusCode': 200,
            'body': json.dumps('Messages sent to SQS successfully!')
        }
    except Exception as e:
        print(f"Error sending message to SQS: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error sending messages to SQS!')
        }
