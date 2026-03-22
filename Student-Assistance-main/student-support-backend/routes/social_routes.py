import json
import os
import urllib.request
import urllib.error

from flask import Blueprint, request, jsonify

from services.chat_engine import process_chat_message


social_routes = Blueprint("social_routes", __name__)


WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")


def _post_json(url, payload, headers=None):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=12) as response:
        content = response.read().decode("utf-8")
        if not content:
            return {}
        return json.loads(content)


def _send_whatsapp_text(to_number, text):
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"sent": False, "reason": "missing_whatsapp_config"}

    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": str(to_number),
        "type": "text",
        "text": {"body": text},
    }
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    try:
        data = _post_json(url, payload, headers=headers)
        return {"sent": True, "response": data}
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = str(e)
        return {"sent": False, "reason": "http_error", "details": error_body}
    except Exception as e:
        return {"sent": False, "reason": "error", "details": str(e)}


def _send_telegram_text(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return {"sent": False, "reason": "missing_telegram_config"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        data = _post_json(url, payload)
        return {"sent": True, "response": data}
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = str(e)
        return {"sent": False, "reason": "http_error", "details": error_body}
    except Exception as e:
        return {"sent": False, "reason": "error", "details": str(e)}


def _send_instagram_text(recipient_id, text):
    if not (INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID):
        return {"sent": False, "reason": "missing_instagram_config"}

    url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/messages"
    payload = {
        "messaging_product": "instagram",
        "recipient": {"id": str(recipient_id)},
        "message": {"text": text},
    }
    headers = {"Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}"}
    try:
        data = _post_json(url, payload, headers=headers)
        return {"sent": True, "response": data}
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = str(e)
        return {"sent": False, "reason": "http_error", "details": error_body}
    except Exception as e:
        return {"sent": False, "reason": "error", "details": str(e)}


@social_routes.route("/integrations/whatsapp/webhook", methods=["GET"])
def whatsapp_verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")

    if mode == "subscribe" and token and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200

    return jsonify({"error": "Webhook verification failed"}), 403


@social_routes.route("/integrations/whatsapp/webhook", methods=["POST"])
def whatsapp_receive_webhook():
    payload = request.get_json(silent=True) or {}
    deliveries = []

    entries = payload.get("entry") or []
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for message in messages:
                from_number = message.get("from")
                text_body = (((message.get("text") or {}).get("body")) or "").strip()
                if not from_number or not text_body:
                    continue
                result = process_chat_message(text_body, user=f"whatsapp:{from_number}", save_log=True)
                sent = _send_whatsapp_text(from_number, result.get("response", ""))
                deliveries.append(
                    {
                        "to": from_number,
                        "incoming": text_body,
                        "response_route": result.get("response_route"),
                        "delivery": sent,
                    }
                )

    return jsonify({"ok": True, "processed": len(deliveries), "deliveries": deliveries}), 200


@social_routes.route("/integrations/instagram/webhook", methods=["GET"])
def instagram_verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")

    if mode == "subscribe" and token and token == INSTAGRAM_VERIFY_TOKEN:
        return challenge, 200

    return jsonify({"error": "Instagram webhook verification failed"}), 403


@social_routes.route("/integrations/instagram/webhook", methods=["POST"])
def instagram_receive_webhook():
    payload = request.get_json(silent=True) or {}
    deliveries = []

    entries = payload.get("entry") or []
    for entry in entries:
        # Messenger-style Instagram webhook
        messaging_events = entry.get("messaging") or []
        for event in messaging_events:
            sender = (event.get("sender") or {}).get("id")
            text_body = ((event.get("message") or {}).get("text") or "").strip()
            if not sender or not text_body:
                continue
            result = process_chat_message(text_body, user=f"instagram:{sender}", save_log=True)
            sent = _send_instagram_text(sender, result.get("response", ""))
            deliveries.append(
                {
                    "to": sender,
                    "incoming": text_body,
                    "response_route": result.get("response_route"),
                    "delivery": sent,
                }
            )

        # Some Instagram payload variants come in changes/value/messages shape.
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for message in messages:
                sender = (message.get("from") or message.get("sender") or {}).get("id")
                if not sender:
                    sender = message.get("from")
                text_body = (((message.get("text") or {}).get("body")) or message.get("text") or "").strip()
                if not sender or not text_body:
                    continue
                result = process_chat_message(text_body, user=f"instagram:{sender}", save_log=True)
                sent = _send_instagram_text(sender, result.get("response", ""))
                deliveries.append(
                    {
                        "to": sender,
                        "incoming": text_body,
                        "response_route": result.get("response_route"),
                        "delivery": sent,
                    }
                )

    return jsonify({"ok": True, "processed": len(deliveries), "deliveries": deliveries}), 200


@social_routes.route("/integrations/telegram/webhook", methods=["POST"])
def telegram_receive_webhook():
    # Treat empty/default placeholder as disabled secret check for local dev.
    secret_required = (
        TELEGRAM_WEBHOOK_SECRET
        and TELEGRAM_WEBHOOK_SECRET != "your_secure_webhook_secret_here"
    )
    if secret_required:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret != TELEGRAM_WEBHOOK_SECRET:
            return jsonify({"error": "Invalid Telegram webhook secret"}), 403

    payload = request.get_json(silent=True) or {}
    message = payload.get("message") or payload.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    user_obj = message.get("from") or {}
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True, "processed": 0}), 200

    user_ref = user_obj.get("username") or user_obj.get("id") or str(chat_id)
    result = process_chat_message(text, user=f"telegram:{user_ref}", save_log=True)
    sent = _send_telegram_text(chat_id, result.get("response", ""))
    if not sent.get("sent"):
        return jsonify(
            {
                "ok": False,
                "processed": 0,
                "chat_id": chat_id,
                "response_route": result.get("response_route"),
                "delivery": sent,
            }
        ), 502

    return jsonify(
        {
            "ok": True,
            "processed": 1,
            "chat_id": chat_id,
            "response_route": result.get("response_route"),
            "delivery": sent,
        }
    ), 200
