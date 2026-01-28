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


def _build_response(status_code: int, payload: dict):
	return {
		'statusCode': status_code,
		'headers': {
			'Content-Type': 'application/json',
			'Access-Control-Allow-Origin': '*',
		},
		'body': json.dumps(payload, default=str),
	}


def _safe_json_body(event):
	body = event.get('body')
	if not body:
		return {}

	if event.get('isBase64Encoded'):
		try:
			body = base64.b64decode(body).decode('utf-8')
		except Exception:
			return {}

	try:
		data = json.loads(body)
	except Exception:
		return {}

	return data if isinstance(data, dict) else {}


def _parse_int(value):
	try:
		parsed = int(value)
		return parsed if parsed > 0 else None
	except (TypeError, ValueError):
		return None


def _extract_request_context(event):
	params = event.get('queryStringParameters') or {}
	path_params = event.get('pathParameters') or {}
	body = _safe_json_body(event)

	identifier = (
		params.get('email')
		or params.get('username')
		or body.get('email')
		or body.get('username')
		or path_params.get('email')
		or path_params.get('username')
		or ''
	).strip().lower()

	meme_id_raw = (
		body.get('memeId')
		or body.get('meme_id')
		or params.get('memeId')
		or params.get('meme_id')
		or path_params.get('memeId')
		or path_params.get('meme_id')
	)
	meme_id = _parse_int(meme_id_raw)

	return identifier, meme_id


def _fetch_user(cursor, identifier: str):
	cursor.execute(
		"SELECT id, email, username FROM users WHERE email=%s OR username=%s LIMIT 1",
		(identifier, identifier),
	)
	return cursor.fetchone()


def _fetch_meme(cursor, meme_id: int, user_id: int):
	cursor.execute(
		"SELECT id, s3_key FROM memes WHERE id=%s AND user_id=%s LIMIT 1",
		(meme_id, user_id),
	)
	return cursor.fetchone()


def lambda_handler(event, _context):
	identifier, meme_id = _extract_request_context(event)

	if not identifier:
		return _build_response(400, {'error': 'email or username is required'})
	if not meme_id:
		return _build_response(400, {'error': 'memeId is required'})

	try:
		conn = _get_connection()
		cursor = conn.cursor(dictionary=True)

		user = _fetch_user(cursor, identifier)
		if not user:
			return _build_response(404, {'error': 'User not found'})

		meme = _fetch_meme(cursor, meme_id, user['id'])
		if not meme:
			return _build_response(404, {'error': 'Meme not found for user'})

		cursor.execute(
			"DELETE FROM memes WHERE id=%s AND user_id=%s",
			(meme_id, user['id']),
		)
		conn.commit()

		payload = {
			'message': 'Meme deleted successfully',
			'memeId': meme_id,
		}
		if meme.get('s3_key'):
			payload['s3Key'] = meme['s3_key']

		return _build_response(200, payload)

	except Exception as exc:  # noqa: BLE001
		print(f"Delete meme lambda error: {exc}")
		if 'conn' in locals():
			conn.rollback()
		return _build_response(500, {'error': 'Unable to delete meme'})
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()
