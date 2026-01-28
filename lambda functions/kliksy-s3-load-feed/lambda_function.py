import json
import math
import os
from datetime import datetime

import mysql.connector


DB_CONFIG = {
	'host': os.environ.get('DB_HOST'),
	'user': os.environ.get('DB_USER'),
	'password': os.environ.get('DB_PASSWORD'),
	'database': os.environ.get('DB_NAME'),
	'port': int(os.environ.get('DB_PORT', '3306')),
}

PAGE_SIZE_DEFAULT = int(os.environ.get('PAGE_SIZE', '8'))
MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', '24'))
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET')
CDN_BASE_URL = (os.environ.get('CDN_BASE_URL') or '').rstrip('/')


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


def _parse_int(value, default):
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def _clamp_page_size(raw_size):
	size = _parse_int(raw_size, PAGE_SIZE_DEFAULT)
	return max(1, min(MAX_PAGE_SIZE, size))


def _build_file_url(key):
	if not key:
		return None
	if CDN_BASE_URL:
		return f"{CDN_BASE_URL}/{key}"
	if UPLOAD_BUCKET:
		return f"https://{UPLOAD_BUCKET}.s3.amazonaws.com/{key}"
	return None


def _serialize_row(row: dict) -> dict:
	created_at = row.get('created_at')
	if isinstance(created_at, datetime):
		created_at = created_at.isoformat()

	return {
		'id': row.get('id'),
		'description': row.get('description') or '',
		'privacy': row.get('privacy'),
		's3Key': row.get('s3_key'),
		'fileUrl': _build_file_url(row.get('s3_key')),
		'fileType': row.get('file_type'),
		'fileSizeBytes': row.get('file_size_bytes'),
		'createdAt': created_at,
		'user': {
			'id': row.get('user_id'),
			'username': row.get('username'),
			'email': row.get('email'),
		},
	}


def lambda_handler(event, _context):
	params = event.get('queryStringParameters') or {}
	page = max(1, _parse_int(params.get('page'), 1))
	page_size = _clamp_page_size(params.get('pageSize'))

	try:
		conn = _get_connection()
		cursor = conn.cursor(dictionary=True)

		where_clause = "m.privacy = 'public'"
		args: list = []

		count_query = f"""
			SELECT COUNT(*) AS total
			FROM memes m
			WHERE {where_clause}
		"""
		cursor.execute(count_query, args)
		total_items = cursor.fetchone().get('total', 0)

		offset = (page - 1) * page_size

		data_query = f"""
			SELECT
				m.id,
				m.user_id,
				m.description,
				m.privacy,
				m.s3_key,
				m.file_type,
				m.file_size_bytes,
				m.created_at,
				u.username,
				u.email
			FROM memes m
			JOIN users u ON u.id = m.user_id
			WHERE {where_clause}
			ORDER BY m.created_at DESC
			LIMIT %s OFFSET %s
		"""
		cursor.execute(data_query, args + [page_size, offset])
		rows = cursor.fetchall()

		total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 1

		payload = {
			'items': [_serialize_row(row) for row in rows],
			'pagination': {
				'page': page,
				'pageSize': page_size,
				'totalItems': total_items,
				'totalPages': total_pages,
			},
		}
		return _build_response(200, payload)

	except Exception as exc:  # noqa: BLE001
		print(f"Feed lambda error: {exc}")
		return _build_response(500, {'error': 'Unable to load feed'})
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()
