import pymysql
import boto3
import os
import json
import re

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
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error getting object from S3: {str(e)}")
        raise e


def remove_non_numeric_chars(input_string):
    return re.sub(r'[^0-9]', '', input_string)


def insert_to_rdb(contents):
    connect_to_rds()
    cur = conn.cursor()

    for content in contents:
        product_name = content['product_name']
        price = int(remove_non_numeric_chars(content['price']))
        category = content['category']
        start_date = content['start_date']
        end_date = content['end_date']
        period_status = content['period_status']
        product_url = content['product_url']
        image_url = ",".join(content['image_url']).strip("[]")

        sql_query = ("""
            INSERT INTO product (name, price, type, start_date, end_date, status, image_url, product_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """)

        try:
            cur.execute(sql_query,
                        (product_name, price, category, start_date, end_date, period_status, image_url, product_url))
        except pymysql.MySQLError as e:
            print(f"Error executing SQL query: {str(e)}")
            conn.rollback()
            raise e

    conn.commit()
    cur.close()
    conn.close()


def lambda_handler(event, context):
    body = json.loads(event['Records'][0]['body'])
    bucket_name = body['bucket_name']
    file_name = body['file_name']

    try:
        s3_content = get_from_s3(bucket_name, file_name)
        contents = json.loads(s3_content)

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
