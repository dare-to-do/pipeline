import pymysql
import boto3
import os
import json
from datetime import datetime, timezone, timedelta

conn = None
db_host = os.environ['HOST']
db_user = os.environ['USER']
db_password = os.environ['PASSWORD']
database = os.environ['DATABASE']
db_port = int(os.environ['PORT'])


def connect_to_rds():
    global conn

    if conn is None:
        try:
            conn = pymysql.connect(host=db_host, user=db_user, passwd=db_password, db=database, port=db_port,
                                   charset='utf8mb4',
                                   write_timeout=2, connect_timeout=5)
            return conn
        except pymysql.MySQLError as e:
            raise e


def get_from_s3(bucket_name, file_name):
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        print("Response:", response)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        raise e


def insert_to_rdb(contents):
    connect_to_rds()
    cur = conn.cursor()

    for content in contents:
        product_name = content['product_name']
        price = content['price']
        category = content['category']
        start_date = content['start_date']
        end_date = content['end_date']
        period_status = content['period_status']
        product_url = content['product_url']
        image_url = content['image_url']
        print(content)
        sql_query = (f"insert into product (name, price, type, start_date, end_date, status, image_url, product_url) "
                     f"values ({product_name}, {price}, {category}, {start_date}, {end_date}, "
                     f"{period_status}, {image_url}, {product_url})")

        cur.execute(sql_query)

    conn.commit()
    conn.close()


def lambda_handler(event, context):
    utc_now = datetime.now(timezone.utc)
    seoul_timezone = timezone(timedelta(hours=9))
    seoul_now = utc_now.astimezone(seoul_timezone)
    now = seoul_now.strftime("%Y/%m/%d/%H")
    print("now:", now)

    bucket_name = event['bucket_name']
    file_name = event['file_name']

    try:
        contents = json.loads(get_from_s3(bucket_name, file_name))
        insert_to_rdb(contents)

        return {
            'statusCode': 200,
            'body': 'Success'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error uploading to RDS: {str(e)}'
        }
