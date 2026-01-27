import base64
import json
import os

import mysql.connector


DB_CONFIG = {
	'host': os.environ.get('DB_HOST'),
	'user': os.environ.get('DB_USER'),
	'password': os.environ.get('DB_PASSWORD'),
	'database': os.environ.get('DB_NAME'),
	'port': int(os.environ.get('DB_PORT', '3306')),
}


def _get_connection():
	return mysql.connector.connect(**DB_CONFIG)


def _log_activity(action: str, details: str) -> None:
	try:
		conn = _get_connection()
		cursor = conn.cursor()
		cursor.execute(
			"INSERT INTO activity_logs (action, details) VALUES (%s, %s)",
			(action, details),
		)
		conn.commit()
	except Exception as exc:  # noqa: BLE001
		print(f"activity log failed: {exc}")
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()


def _parse_body(event):
	if 'body' in event:
		body = event['body']
		if event.get('isBase64Encoded'):
			body = base64.b64decode(body).decode('utf-8')
		return json.loads(body)
	return event


def _build_response(status_code: int, payload: dict):
	return {
		'statusCode': status_code,
		'headers': {
			'Content-Type': 'application/json',
			'Access-Control-Allow-Origin': '*',
		},
		'body': json.dumps(payload),
	}


def lambda_handler(event, context):
	try:
		body = _parse_body(event)
		identifier = (body.get('email') or body.get('username') or '').strip().lower()

		if not identifier:
			return _build_response(400, {'error': 'email or username is required'})

		conn = _get_connection()
		cursor = conn.cursor(dictionary=True)

		cursor.execute(
			"SELECT id, email, username FROM users WHERE email=%s OR username=%s LIMIT 1",
			(identifier, identifier),
		)
		user = cursor.fetchone()

		if not user:
			return _build_response(404, {'error': 'User not found'})

		_log_activity('LOGOUT', f"user logged out: {user['email']}")

		return _build_response(200, {
			'message': 'Logout recorded',
			'user': {
				'id': user['id'],
				'email': user['email'],
				'username': user['username'],
			}
		})

	except Exception as exc:  # noqa: BLE001
		print(f"Error: {exc}")
		return _build_response(500, {'error': 'Internal server error'})
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()
