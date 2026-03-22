from datetime import datetime
import json
import os
from database import chat_logs_collection


def save_chat_log(
    user="guest",
    message="",
    response="",
    sentiment="neutral",
    matched=None,
    matched_intent=None,
    confidence=None,
    match_source=None,
):
    """
    Save chatbot interaction to MongoDB chat_logs collection.
    Falls back to a local JSONL file if MongoDB is unavailable.
    """
    log_data = {
        "user": user,
        "message": message,
        "response": response,
        "sentiment": sentiment,
        "matched": matched,
        "matched_intent": matched_intent,
        "confidence": confidence,
        "match_source": match_source,
        "timestamp": datetime.utcnow()
    }

    try:
        # Keep logs ASCII-only for Windows console compatibility.
        print("[chat_logger] Saving chat log:", log_data)

        result = chat_logs_collection.insert_one(log_data)

        print(f"[chat_logger] Chat log saved successfully. ID: {result.inserted_id}")
        return result.inserted_id

    except Exception as e:
        print("[chat_logger] Failed to save chat log:", str(e))

        # Fallback so logs are not lost when MongoDB is unavailable.
        try:
            fallback_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_file = os.path.join(fallback_dir, "chat_logs_fallback.jsonl")

            fallback_payload = {
                **log_data,
                "timestamp": log_data["timestamp"].isoformat(),
                "mongo_error": str(e)
            }

            with open(fallback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(fallback_payload, ensure_ascii=True) + "\n")

            print("[chat_logger] Saved fallback log to:", fallback_file)

        except Exception as fallback_error:
            print("[chat_logger] Fallback log save failed:", str(fallback_error))

        return None
