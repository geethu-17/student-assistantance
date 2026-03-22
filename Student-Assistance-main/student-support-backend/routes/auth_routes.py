from flask import Blueprint, request, jsonify
from database import users_collection
import bcrypt
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from services.password_reset_delivery import send_password_reset_email, email_delivery_ready

auth_routes = Blueprint("auth_routes", __name__)
RESET_TOKEN_TTL_MINUTES = 20


def _hash_token(raw_token):
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


# -----------------------------
# Register User
# -----------------------------
@auth_routes.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    registration_number = (data.get("registration_number") or "").strip()

    if not name or not email or not password or not registration_number:
        return jsonify({"error": "name, email, registration_number and password are required"}), 400

    try:
        existing_user = users_collection.find_one({
            "email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}
        })

        if existing_user:
            return jsonify({"error": "Email already registered"}), 409

        existing_registration = users_collection.find_one({
            "registration_number": {"$regex": f"^{re.escape(registration_number)}$", "$options": "i"}
        })
        if existing_registration:
            return jsonify({"error": "Registration number already registered"}), 409

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        user = {
            "name": name,
            "email": email,
            "registration_number": registration_number,
            "password": hashed_password,
            "role": "student"
        }

        users_collection.insert_one(user)

        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({
            "error": "Database unavailable",
            "details": str(e)
        }), 503


# -----------------------------
# Login User
# -----------------------------
@auth_routes.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    identifier = (data.get("identifier") or "").strip()
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"error": "Missing login credentials"}), 400

    try:
        identifier_email = identifier.lower()
        user = users_collection.find_one({
            "$or": [
                {"email": identifier_email},
                {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                {"registration_number": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}}
            ]
        })

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check password
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            return jsonify({"error": "Invalid password"}), 401

        return jsonify({
            "message": "Login successful",
            "user": {
                "name": user["name"],
                "email": user["email"],
                "registration_number": user.get("registration_number"),
                "role": user["role"]
            }
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Database unavailable",
            "details": str(e)
        }), 503


# -----------------------------
# Forgot Password (Student)
# -----------------------------
@auth_routes.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        return jsonify({"error": "identifier is required"}), 400

    try:
        user = users_collection.find_one({
            "$or": [
                {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                {"registration_number": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
            ]
        })

        if not user:
            return jsonify({"error": "User not found"}), 404

        reset_token = secrets.token_urlsafe(24)
        token_hash = _hash_token(reset_token)
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)

        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "password_reset_token_hash": token_hash,
                "password_reset_token_expires_at": expires_at,
                "password_reset_requested_at": datetime.utcnow(),
            }}
        )

        delivery = send_password_reset_email(
            recipient_email=user.get("email"),
            reset_token=reset_token,
            expires_in_minutes=RESET_TOKEN_TTL_MINUTES,
            audience="student",
        )

        # If SMTP is configured and delivery succeeds, avoid exposing token in API response.
        if delivery.get("sent"):
            return jsonify({
                "message": "Password reset token sent to your registered email",
                "identifier": identifier,
                "delivery": {"sent": True, "channel": "email"},
                "expires_in_minutes": RESET_TOKEN_TTL_MINUTES,
            }), 200

        # Dev fallback: return token when email cannot be delivered.
        return jsonify({
            "message": "Password reset token generated (email delivery unavailable)",
            "identifier": identifier,
            "reset_token": reset_token,
            "expires_in_minutes": RESET_TOKEN_TTL_MINUTES,
            "delivery": {
                "sent": False,
                "channel": "email",
                "reason": delivery.get("reason"),
                "details": delivery.get("message"),
                "email_configured": email_delivery_ready(),
            },
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Database unavailable",
            "details": str(e)
        }), 503


# -----------------------------
# Reset Password (Student)
# -----------------------------
@auth_routes.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}

    identifier = (data.get("identifier") or "").strip()
    reset_token = (data.get("reset_token") or "").strip()
    new_password = data.get("new_password") or ""

    if not identifier or not reset_token or not new_password:
        return jsonify({"error": "identifier, reset_token and new_password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "new_password must be at least 6 characters"}), 400

    try:
        user = users_collection.find_one({
            "$or": [
                {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                {"registration_number": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
            ]
        })
        if not user:
            return jsonify({"error": "User not found"}), 404

        expected_hash = user.get("password_reset_token_hash")
        expires_at = user.get("password_reset_token_expires_at")
        if not expected_hash or not expires_at:
            return jsonify({"error": "No active reset token. Request forgot password first"}), 400

        if datetime.utcnow() > expires_at:
            return jsonify({"error": "Reset token expired. Request a new one"}), 400

        if _hash_token(reset_token) != expected_hash:
            return jsonify({"error": "Invalid reset token"}), 401

        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"password": hashed_password},
             "$unset": {
                 "password_reset_token_hash": "",
                 "password_reset_token_expires_at": "",
                 "password_reset_requested_at": "",
             }}
        )

        return jsonify({"message": "Password reset successful"}), 200
    except Exception as e:
        return jsonify({
            "error": "Database unavailable",
            "details": str(e)
        }), 503
