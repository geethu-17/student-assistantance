import os
from functools import wraps

from flask import jsonify, request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, BadTimeSignature, SignatureExpired


ADMIN_TOKEN_SECRET = os.getenv("ADMIN_TOKEN_SECRET") or os.getenv("FLASK_SECRET_KEY") or "change-this-admin-secret"
ADMIN_TOKEN_SALT = os.getenv("ADMIN_TOKEN_SALT", "student-support-admin")
ADMIN_TOKEN_EXPIRES_SECONDS = int(os.getenv("ADMIN_TOKEN_EXPIRES_SECONDS", "28800"))


def _serializer():
    return URLSafeTimedSerializer(ADMIN_TOKEN_SECRET, salt=ADMIN_TOKEN_SALT)


def create_admin_token(payload):
    return _serializer().dumps(payload)


def decode_admin_token(token):
    return _serializer().loads(token, max_age=ADMIN_TOKEN_EXPIRES_SECONDS)


def _extract_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    return token or None


def require_admin_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "Missing admin token"}), 401

        try:
            g.admin = decode_admin_token(token)
        except SignatureExpired:
            return jsonify({"error": "Admin token expired"}), 401
        except (BadSignature, BadTimeSignature):
            return jsonify({"error": "Invalid admin token"}), 401
        except Exception:
            return jsonify({"error": "Unable to verify admin token"}), 401

        return fn(*args, **kwargs)

    return wrapper
