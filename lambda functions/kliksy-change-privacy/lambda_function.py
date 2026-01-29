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


def _normalize_meme_id(value):
	if value is None:
		return None
	meme_id = str(value).strip()
	return meme_id or None


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
	meme_id = _normalize_meme_id(meme_id_raw)

	privacy = (
		body.get('privacy')
		or params.get('privacy')
		or path_params.get('privacy')
		or ''
	).strip().lower()

	return identifier, meme_id, privacy


def _fetch_user(cursor, identifier: str):
	cursor.execute(
		"SELECT id, email, username FROM users WHERE email=%s OR username=%s LIMIT 1",
		(identifier, identifier),
	)
	return cursor.fetchone()


def _fetch_meme(cursor, meme_id: str, user_id: int):
	cursor.execute(
		"SELECT id, privacy FROM memes WHERE id=%s AND user_id=%s LIMIT 1",
		(meme_id, user_id),
	)
	return cursor.fetchone()


def lambda_handler(event, _context):
	identifier, meme_id, privacy = _extract_request_context(event)

	if not identifier:
		return _build_response(400, {'error': 'email or username is required'})
	if not meme_id:
		return _build_response(400, {'error': 'memeId is required'})
	if not privacy or privacy not in ('public', 'private'):
		return _build_response(400, {'error': 'privacy must be either "public" or "private"'})

	try:
		conn = _get_connection()
		cursor = conn.cursor(dictionary=True)

		user = _fetch_user(cursor, identifier)
		if not user:
			return _build_response(404, {'error': 'User not found'})

		meme = _fetch_meme(cursor, meme_id, user['id'])
		if not meme:
			return _build_response(404, {'error': 'Meme not found for user'})

		old_privacy = meme['privacy']

		cursor.execute(
			"UPDATE memes SET privacy=%s WHERE id=%s AND user_id=%s",
			(privacy, meme_id, user['id']),
		)
		conn.commit()

		_log_activity(
			'UPDATE_PRIVACY',
			f"user changed meme privacy: {user['email']} - meme {meme_id} from {old_privacy} to {privacy}"
		)

		return _build_response(200, {
			'message': 'Privacy updated successfully',
			'memeId': meme_id,
			'oldPrivacy': old_privacy,
			'newPrivacy': privacy,
		})

	except Exception as exc:  # noqa: BLE001
		print(f"Change privacy lambda error: {exc}")
		if 'conn' in locals():
			conn.rollback()
		return _build_response(500, {'error': 'Unable to update privacy'})
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()
