import base64
import json
import os
import uuid

import boto3
import mysql.connector


DB_CONFIG = {
	'host': os.environ.get('DB_HOST'),
	'user': os.environ.get('DB_USER'),
	'password': os.environ.get('DB_PASSWORD'),
	'database': os.environ.get('DB_NAME'),
	'port': int(os.environ.get('DB_PORT', '3306')),
}
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET')
MAX_FILE_BYTES = int(os.environ.get('MAX_FILE_BYTES', str(10 * 1024 * 1024)))  # default 10 MB

s3_client = boto3.client('s3')

def _get_connection():
	return mysql.connector.connect(**DB_CONFIG)


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


def _fetch_user(cursor, identifier: str):
	cursor.execute(
		"SELECT id, email, username FROM users WHERE email=%s OR username=%s LIMIT 1",
		(identifier, identifier),
	)
	return cursor.fetchone()


def _store_file_to_s3(user_id: int, file_data: bytes, content_type: str) -> str:
	if not UPLOAD_BUCKET:
		raise ValueError('UPLOAD_BUCKET environment variable is not set')

	if len(file_data) > MAX_FILE_BYTES:
		raise ValueError('File exceeds maximum allowed size')

	file_ext = content_type.split('/')[-1] if '/' in content_type else 'bin'
	key = f"uploads/{user_id}/{uuid.uuid4()}.{file_ext}"

	s3_client.put_object(
		Bucket=UPLOAD_BUCKET,
		Key=key,
		Body=file_data,
		ContentType=content_type,
	)

	return key

def lambda_handler(event, context):
	try:
		body = _parse_body(event)
		upload_payload = body.get('file') or {}
		identifier = (body.get('email') or body.get('username') or '').strip().lower()
		description = (body.get('description') or '').strip()
		privacy = (body.get('privacy') or 'public').lower()

		if privacy not in {'public', 'private'}:
			return _build_response(400, {'error': 'privacy must be public or private'})

		if not identifier:
			return _build_response(400, {'error': 'email or username is required'})

		encoded_data = upload_payload.get('data')
		content_type = upload_payload.get('contentType') or 'application/octet-stream'
		file_size_bytes = upload_payload.get('sizeBytes')

		if not encoded_data:
			return _build_response(400, {'error': 'file data is required'})

		file_bytes = base64.b64decode(encoded_data)
		if file_size_bytes is not None and int(file_size_bytes) != len(file_bytes):
			file_size_bytes = len(file_bytes)

		conn = _get_connection()
		cursor = conn.cursor(dictionary=True)

		user = _fetch_user(cursor, identifier)
		if not user:
			return _build_response(404, {'error': 'User not found'})

		s3_key = _store_file_to_s3(user['id'], file_bytes, content_type)
		meme_id = str(uuid.uuid4())

		cursor.execute(
			"""
			INSERT INTO memes (
				id, user_id, s3_key, description, privacy, file_type, file_size_bytes
			) VALUES (%s, %s, %s, %s, %s, %s, %s)
			""",
			(
				meme_id,
				user['id'],
				s3_key,
				description,
				privacy,
				content_type,
				file_size_bytes or len(file_bytes),
			),
		)
		conn.commit()

		file_url = f"https://{UPLOAD_BUCKET}.s3.amazonaws.com/{s3_key}"

		return _build_response(201, {
			'message': 'Upload successful',
			'meme': {
				'id': meme_id,
				'user': {
					'id': user['id'],
					'email': user['email'],
					'username': user['username'],
				},
				'description': description,
				'privacy': privacy,
				's3Key': s3_key,
				'fileUrl': file_url,
				'fileType': content_type,
				'fileSizeBytes': file_size_bytes or len(file_bytes),
			}
		})

	except ValueError as validation_error:
		return _build_response(400, {'error': str(validation_error)})
	except Exception as exc:  # noqa: BLE001
		print(f"Error: {exc}")
		return _build_response(500, {'error': 'Internal server error'})
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()
