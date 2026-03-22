from flask import Blueprint, request, jsonify
from model.chatbot_model import get_response
from database import intents_collection, academic_calendar_collection
from services.chat_logger import save_chat_log
from utils.sentiment_analyzer import detect_sentiment

import random

chatbot_routes = Blueprint("chatbot_routes", __name__)


@chatbot_routes.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    user = data.get("user", "guest")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    try:

        message_lower = message.lower()

        # -----------------------------
        # Detect sentiment
        # -----------------------------
        sentiment = detect_sentiment(message)

        response = None

        # -----------------------------
        # Admission Eligibility Feature
        # -----------------------------
        if "eligibility" in message_lower:

            response = (
                "To check eligibility for B.Tech programs, please provide "
                "your stream (MPC/BiPC) and marks percentage."
            )

        # -----------------------------
        # Application Status Feature
        # -----------------------------
        elif "application status" in message_lower:

            response = (
                "Please provide your registration number to check your "
                "application status."
            )

        # -----------------------------
        # Academic Calendar Feature
        # -----------------------------
        elif "academic calendar" in message_lower or "semester start" in message_lower:

            events = list(
                academic_calendar_collection.find({}, {"_id": 0})
            )

            if events:
                formatted_events = "\n".join([str(event) for event in events])
                response = f"Upcoming academic events:\n{formatted_events}"
            else:
                response = "Academic calendar is currently not available."

        # -----------------------------
        # Counseling Support Feature
        # -----------------------------
        elif "counseling" in message_lower or "mental health" in message_lower:

            response = (
                "If you would like counseling support, you can submit a "
                "request through the student support system."
            )

        # -----------------------------
        # Default ML Chatbot
        # -----------------------------
        if not response:

            response = get_response(message)

            # Pattern fallback if ML fails
            if response.lower().startswith("sorry"):

                intents = intents_collection.find()

                for intent in intents:
                    for pattern in intent.get("patterns", []):

                        if pattern.lower() in message_lower:
                            response = random.choice(intent.get("responses", []))
                            break
                    else:
                        continue
                    break

        # -----------------------------
        # Mental Health Suggestion
        # -----------------------------
        if sentiment == "negative":
            response += (
                " If you're feeling stressed, you can also reach out to "
                "the student counseling center."
            )

        # -----------------------------
        # Save Chat Log
        # -----------------------------

        try:
            print("Calling save_chat_log...")
            save_chat_log(
                user=user,
                message=message,
                response=response,
                sentiment=sentiment
            )
            print("Chat log saved successfully")

        except Exception as log_error:
            print("Chat log failed:", log_error)

        return jsonify({
            "response": response,
            "sentiment": sentiment
        })

    except Exception as e:

        print("Chatbot error:", e)

        return jsonify({
            "response": "Sorry, something went wrong."
        }), 500