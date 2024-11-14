import requests
import os
from datetime import datetime, timezone, timedelta

text = "scraping failed"
slack_url = os.environ['SLACK_URL']

utc_now = datetime.now(timezone.utc)
seoul_timezone = timezone(timedelta(hours=9))
seoul_now = utc_now.astimezone(seoul_timezone)


def send_msg_to_slack(url, msg, title):
    slack_data = {"attachments": [{"color": "#e50000", "fields": [{"title": title, "value": msg, "short": "true"}]}]}
    requests.post(url, json=slack_data).raise_for_status()


def lambda_handler(event, context):
    site_name = event['from']
    msg = f"{site_name} Scraping Failed at {seoul_now}"
    title = f"{site_name} 스크래핑 실패"
    send_msg_to_slack(slack_url, msg, title)
    return {'statusCode': 200, 'body': 'Post SUCCESS'}
