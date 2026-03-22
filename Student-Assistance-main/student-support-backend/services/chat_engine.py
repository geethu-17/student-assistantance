from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

from chatbot_model import get_response
from services.query_router import try_handle_functional_query
from services.chat_logger import save_chat_log
from utils.sentiment_analyzer import detect_sentiment


SUPPORTED_LANGUAGES = ["en", "hi", "te", "ta", "kn"]


def translate_to_en(text, source_lang):
    return GoogleTranslator(source=source_lang, target="en").translate(text)


def translate_from_en(text, target_lang):
    return GoogleTranslator(source="en", target=target_lang).translate(text)


def process_chat_message(message, user="guest", save_log=True):
    message = (message or "").strip()
    if not message:
        return {"error": "message is required", "status_code": 400}

    final_response = None
    sentiment = "neutral"
    user_lang = "en"
    matched = None
    matched_intent = None
    match_source = None
    confidence = None
    response_route = "unknown"

    try:
        try:
            user_lang = detect(message)
        except LangDetectException:
            user_lang = "en"

        if user_lang not in SUPPORTED_LANGUAGES:
            user_lang = "en"

        translated_message = translate_to_en(message, user_lang) if user_lang != "en" else message
        translated_message = translated_message.lower()

        sentiment = detect_sentiment(translated_message)

        route_result = try_handle_functional_query(translated_message, user_identifier=user)
        if route_result.get("handled"):
            response_en = route_result.get("response")
            matched = route_result.get("matched")
            matched_intent = route_result.get("matched_intent")
            match_source = route_result.get("match_source")
            response_route = "functional_module"
        else:
            chatbot_result = get_response(translated_message, return_meta=True)
            response_en = chatbot_result.get("response")
            matched = chatbot_result.get("matched")
            matched_intent = chatbot_result.get("intent_tag")
            match_source = chatbot_result.get("match_source")
            confidence = chatbot_result.get("confidence")
            response_route = "faq_model"

        final_response = translate_from_en(response_en, user_lang) if user_lang != "en" else response_en

    except Exception as e:
        print("Translation or routing error:", e)
        fallback_result = get_response(message, return_meta=True)
        final_response = fallback_result.get("response")
        matched = fallback_result.get("matched")
        matched_intent = fallback_result.get("intent_tag")
        match_source = fallback_result.get("match_source")
        confidence = fallback_result.get("confidence")
        sentiment = "neutral"
        user_lang = "en"
        response_route = "faq_model_error_fallback"

    if save_log:
        try:
            save_chat_log(
                user=user,
                message=message,
                response=final_response,
                sentiment=sentiment,
                matched=matched,
                matched_intent=matched_intent,
                match_source=match_source,
                confidence=confidence,
            )
        except Exception as log_error:
            print("Chat log error:", log_error)

    return {
        "response": final_response,
        "language": user_lang,
        "sentiment": sentiment,
        "response_route": response_route,
        "status_code": 200,
    }
