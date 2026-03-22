from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load env variables
load_dotenv(Path(__file__).resolve().parent / ".env")

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if TELEGRAM_BOT_TOKEN
    else None
)

# Import your modules
from routes.auth_routes import auth_routes
from routes.admin_routes import admin_routes
from routes.social_routes import social_routes
from routes.ai_features_routes import ai_features_routes
from services.chat_engine import process_chat_message
from database import check_mongo_connection, DB_NAME

from student.admission_routes import admission_routes
from student.academic_routes import academic_routes
from student.counseling_routes import counseling_routes
from student.financial_routes import financial_routes
from student.campus_routes import campus_routes

# Initialize app
app = Flask(__name__)

allowed_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

frontend_base_url = os.getenv("FRONTEND_BASE_URL", "").strip()
if frontend_base_url:
    allowed_origins.add(frontend_base_url.rstrip("/"))

CORS(
    app,
    resources={r"/api/*": {"origins": list(allowed_origins)}},
    supports_credentials=False,
)

# Register routes
app.register_blueprint(auth_routes, url_prefix="/api")
app.register_blueprint(admin_routes, url_prefix="/api")
app.register_blueprint(social_routes, url_prefix="/api")
app.register_blueprint(ai_features_routes, url_prefix="/api")

app.register_blueprint(admission_routes, url_prefix="/api")
app.register_blueprint(academic_routes, url_prefix="/api")
app.register_blueprint(counseling_routes, url_prefix="/api")
app.register_blueprint(financial_routes, url_prefix="/api")
app.register_blueprint(campus_routes, url_prefix="/api")


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Student support backend is running"
    })


@app.route("/api/db-status", methods=["GET"])
def db_status():
    ok, message = check_mongo_connection()
    status_code = 200 if ok else 503
    return jsonify({
        "connected": ok,
        "database": DB_NAME,
        "message": message
    }), status_code


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    user = data.get("user", "guest")

    result = process_chat_message(message, user=user, save_log=True)

    status = result.pop("status_code", 200)
    if "error" in result:
        return jsonify(result), status

    return jsonify(result), status


def _is_webhook_secret_valid(incoming_secret):
    # Allow unset or placeholder secret for local development.
    if not TELEGRAM_WEBHOOK_SECRET or TELEGRAM_WEBHOOK_SECRET == "your_secure_webhook_secret_here":
        return True
    return incoming_secret == TELEGRAM_WEBHOOK_SECRET


def _send_telegram_message(chat_id, text):
    if not TELEGRAM_API_URL:
        return {
            "ok": False,
            "error": "TELEGRAM_BOT_TOKEN is missing. Cannot send Telegram reply."
        }

    try:
        telegram_response = requests.post(
            TELEGRAM_API_URL,
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        try:
            telegram_json = telegram_response.json()
        except ValueError:
            telegram_json = {"description": telegram_response.text}

        if telegram_response.ok and telegram_json.get("ok", False):
            return {"ok": True}

        return {
            "ok": False,
            "error": telegram_json.get("description", "Telegram API sendMessage failed"),
            "status_code": telegram_response.status_code,
        }
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    incoming_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not _is_webhook_secret_valid(incoming_secret):
        return jsonify({"ok": False, "error": "invalid webhook secret"}), 403

    data = request.get_json(silent=True) or {}
    print("Telegram Update:", data)

    if not data:
        return jsonify({"ok": False, "error": "no data"}), 400

    incoming_message = data.get("message") or data.get("edited_message")
    if not incoming_message:
        return jsonify({"ok": True, "processed": 0, "message": "unsupported update type"}), 200

    chat_id = ((incoming_message.get("chat") or {}).get("id"))
    text = (incoming_message.get("text") or "").strip()

    if not chat_id:
        return jsonify({"ok": False, "error": "missing chat id"}), 400

    if not text:
        return jsonify({"ok": True, "processed": 0, "message": "no text"}), 200

    try:
        result = process_chat_message(text, user=str(chat_id), save_log=True)
        reply = result.get("response", "Sorry, I didn't understand that.")
    except Exception as e:
        print("Telegram processing error:", e)
        reply = "Server error. Try again later."

    send_result = _send_telegram_message(chat_id, reply)
    if not send_result.get("ok"):
        print("Telegram send error:", send_result)
        return jsonify({
            "ok": False,
            "processed": 0,
            "error": send_result.get("error"),
        }), 502

    return jsonify({"ok": True, "processed": 1, "reply": reply}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
