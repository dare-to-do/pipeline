import requests
import os
from datetime import datetime, timezone, timedelta

slack_url = os.environ['SLACK_URL']

utc_now = datetime.now(timezone.utc)
seoul_timezone = timezone(timedelta(hours=9))
seoul_now = utc_now.astimezone(seoul_timezone)


def send_msg_to_slack(url, msg, title):
    slack_data = {"attachments": [{"color": "#e50000", "fields": [{"title": title, "value": msg, "short": "true"}]}]}
    requests.post(url, json=slack_data).raise_for_status()


def lambda_handler(event, context):
    site_name = event['from']
    title = f"{site_name} 스크래핑 실패"
    msg = f"{site_name}에서 데이터를 못 가져왔습니다 😭 {seoul_now}"
    send_msg_to_slack(slack_url, msg, title)
    return {'statusCode': 200, 'body': 'Post SUCCESS'}
