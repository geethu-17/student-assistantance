from flask import Blueprint, request, jsonify

from services.chat_engine import process_chat_message
from services.faq_generator import generate_faq_items


ai_features_routes = Blueprint("ai_features_routes", __name__)


@ai_features_routes.route("/ai/faqs/generated", methods=["GET"])
def generated_faqs():
    limit = request.args.get("limit", 10)
    items = generate_faq_items(limit=limit)
    return jsonify(
        {
            "items": items,
            "count": len(items),
            "feature": "ai_generated_faqs",
        }
    )


@ai_features_routes.route("/ai/voice/capabilities", methods=["GET"])
def voice_capabilities():
    # Backend supports transcript-based voice workflows.
    # Frontend can use browser speech-to-text and text-to-speech directly.
    return jsonify(
        {
            "feature": "voice_enabled_interaction",
            "input": {
                "mode": "transcript_text",
                "field": "transcript",
            },
            "output": {
                "tts_text_field": "voice.tts_text",
                "language_field": "language",
            },
        }
    )


@ai_features_routes.route("/ai/voice/chat", methods=["POST"])
def voice_chat():
    data = request.get_json(silent=True) or {}
    transcript = (data.get("transcript") or data.get("message") or "").strip()
    user = (data.get("user") or "voice_user").strip()

    if not transcript:
        return jsonify({"error": "transcript is required"}), 400

    result = process_chat_message(transcript, user=user, save_log=True)
    status = result.pop("status_code", 200)
    if "error" in result:
        return jsonify(result), status

    response_text = result.get("response", "")

    return jsonify(
        {
            "transcript": transcript,
            "response": response_text,
            "language": result.get("language"),
            "sentiment": result.get("sentiment"),
            "response_route": result.get("response_route"),
            "voice": {
                "tts_text": response_text,
            },
        }
    ), 200
