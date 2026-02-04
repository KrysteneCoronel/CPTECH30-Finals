import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key


LOG_TABLE = os.environ.get('LOG_TABLE', 'KliksyLogs')
GLOBAL_INDEX = os.environ.get('LOG_GSI_NAME', 'GlobalTimeline')
GLOBAL_PARTITION = os.environ.get('GLOBAL_LOG_PK', 'ALL')
MAX_ITEMS = int(os.environ.get('LOGS_MAX_ITEMS', '50'))

dynamodb = boto3.resource('dynamodb')
log_table = dynamodb.Table(LOG_TABLE)


def _coerce(value):
	if isinstance(value, list):
		return [_coerce(item) for item in value]
	if isinstance(value, dict):
		return {key: _coerce(val) for key, val in value.items()}
	if isinstance(value, Decimal):
		if value % 1 == 0:
			return int(value)
		return float(value)
	return value


def lambda_handler(event, context):
	try:
		params = event.get('queryStringParameters') or {}
		viewer = (params.get('userID') or params.get('viewer') or '').strip()

		query_kwargs = {
			'ScanIndexForward': False,
			'Limit': MAX_ITEMS,
		}
		if viewer:
			query_kwargs['KeyConditionExpression'] = Key('userID').eq(viewer)
		else:
			query_kwargs['IndexName'] = GLOBAL_INDEX
			query_kwargs['KeyConditionExpression'] = Key('globalKey').eq(GLOBAL_PARTITION)

		response = log_table.query(**query_kwargs)
		logs = [_coerce(item) for item in response.get('Items', [])]

		return {
			'statusCode': 200,
			'headers': {
				'Content-Type': 'application/json',
				'Access-Control-Allow-Origin': '*',
			},
			'body': json.dumps(logs),
		}
	except Exception as exc:  # noqa: BLE001
		print(f"Error fetching logs: {exc}")
		return {
			'statusCode': 500,
			'headers': {
				'Content-Type': 'application/json',
				'Access-Control-Allow-Origin': '*',
			},
			'body': json.dumps({'error': 'Unable to fetch logs'}),
		}
