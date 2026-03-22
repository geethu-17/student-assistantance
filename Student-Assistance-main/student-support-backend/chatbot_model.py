import os
import json
import numpy as np
import pickle
import shutil
import tempfile
from pathlib import Path

from database import intents_collection

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from tensorflow.keras.models import load_model
from tensorflow.keras.layers import Embedding
from tensorflow.keras.preprocessing.sequence import pad_sequences


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"
INTENTS_FILE = BASE_DIR / "intents.json"


# -----------------------------
# Load Model Components
# -----------------------------
model = None
tokenizer = None
label_encoder = None
max_len = None


def _remove_key_deep(value, key_to_remove):
    if isinstance(value, dict):
        return {
            k: _remove_key_deep(v, key_to_remove)
            for k, v in value.items()
            if k != key_to_remove
        }
    if isinstance(value, list):
        return [_remove_key_deep(item, key_to_remove) for item in value]
    return value


def _load_model_with_compat(model_path):
    """
    Try normal loading first.
    If deserialization fails due unsupported config keys (e.g. quantization_config),
    rewrite model_config in a temporary copy and retry load.
    """
    try:
        return load_model(str(model_path), compile=False)
    except Exception as original_error:
        error_text = str(original_error)
        if "quantization_config" not in error_text:
            raise

        try:
            class CompatEmbedding(Embedding):
                def __init__(self, *args, **kwargs):
                    # Keras version mismatch can pass this unknown key from older/newer model configs.
                    kwargs.pop("quantization_config", None)
                    super().__init__(*args, **kwargs)

            # First try custom-object based deserialization (fast path).
            try:
                return load_model(
                    str(model_path),
                    compile=False,
                    custom_objects={"Embedding": CompatEmbedding},
                )
            except Exception:
                pass

            import h5py

            with h5py.File(str(model_path), "r") as f:
                raw_config = f.attrs.get("model_config")

            if raw_config is None:
                raise

            if isinstance(raw_config, bytes):
                raw_config = raw_config.decode("utf-8")

            parsed_config = json.loads(raw_config)
            cleaned_config = _remove_key_deep(parsed_config, "quantization_config")

            temp_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
            temp_file.close()
            temp_model_path = Path(temp_file.name)

            shutil.copy2(model_path, temp_model_path)
            with h5py.File(str(temp_model_path), "r+") as f:
                f.attrs["model_config"] = json.dumps(cleaned_config).encode("utf-8")

            try:
                return load_model(str(temp_model_path), compile=False)
            finally:
                try:
                    temp_model_path.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            raise original_error


try:
    model = _load_model_with_compat(MODEL_DIR / "chatbot_model.h5")
    with (MODEL_DIR / "tokenizer.pickle").open("rb") as f:
        tokenizer = pickle.load(f)
    with (MODEL_DIR / "label_encoder.pickle").open("rb") as f:
        label_encoder = pickle.load(f)
    with (MODEL_DIR / "max_len.pickle").open("rb") as f:
        max_len = pickle.load(f)
except Exception as e:
    # Keep backend available even when model deserialization fails in some environments.
    print("Model initialization failed; using pattern fallback only:", e)


# -----------------------------
# Local Intents Fallback
# -----------------------------
def load_local_intents():
    try:
        with INTENTS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("intents", [])
    except Exception as e:
        print("Failed to load local intents:", e)
        return []


LOCAL_INTENTS = load_local_intents()


def normalize_intent(intent_obj):
    tag = intent_obj.get("tag") or intent_obj.get("intent")
    patterns = intent_obj.get("patterns") or intent_obj.get("text") or []
    responses = intent_obj.get("responses") or []
    return {
        "tag": tag,
        "patterns": patterns,
        "responses": responses
    }


NORMALIZED_LOCAL_INTENTS = [normalize_intent(i) for i in LOCAL_INTENTS]
LOCAL_INTENTS_BY_TAG = {
    intent.get("tag"): intent
    for intent in NORMALIZED_LOCAL_INTENTS
    if intent.get("tag")
}

UNKNOWN_RESPONSE = "Sorry, I didn't understand your question."


def get_all_intents():
    try:
        return [normalize_intent(i) for i in intents_collection.find()]
    except Exception:
        return NORMALIZED_LOCAL_INTENTS


def get_intent_by_tag(tag):
    try:
        intent = intents_collection.find_one({
            "$or": [{"tag": tag}, {"intent": tag}]
        })
        if intent:
            return normalize_intent(intent)
    except Exception:
        pass

    return LOCAL_INTENTS_BY_TAG.get(tag)


# -----------------------------
# Pattern Fallback Search
# -----------------------------
def pattern_fallback(user_input):
    user_input = user_input.lower()

    intents = get_all_intents()

    for intent in intents:
        for pattern in intent.get("patterns", []):
            p = pattern.lower().strip()
            if not p:
                continue
            if p in user_input or user_input in p:
                responses = intent.get("responses", [])
                if responses:
                    return np.random.choice(responses), intent.get("tag")

    return None, None


def _response_result(response, matched=False, intent_tag=None, confidence=None, source="unknown"):
    return {
        "response": response,
        "matched": matched,
        "intent_tag": intent_tag,
        "confidence": float(confidence) if confidence is not None else None,
        "match_source": source,
    }


# -----------------------------
# Get Response
# -----------------------------
def get_response(user_input, return_meta=False):

    if not user_input.strip():
        result = _response_result(
            response="Please ask a valid question.",
            matched=False,
            intent_tag=None,
            confidence=None,
            source="invalid_input",
        )
        return result if return_meta else result["response"]

    try:
        if not all([model is not None, tokenizer is not None, label_encoder is not None, max_len is not None]):
            fallback, fallback_intent = pattern_fallback(user_input)
            if fallback:
                result = _response_result(
                    response=fallback,
                    matched=True,
                    intent_tag=fallback_intent,
                    confidence=None,
                    source="pattern_fallback",
                )
                return result if return_meta else result["response"]
            result = _response_result(
                response=UNKNOWN_RESPONSE,
                matched=False,
                intent_tag=None,
                confidence=None,
                source="model_unavailable",
            )
            return result if return_meta else result["response"]

        # Convert text to sequence
        sequence = tokenizer.texts_to_sequences([user_input])

        if not sequence or not sequence[0]:
            fallback, fallback_intent = pattern_fallback(user_input)
            if fallback:
                result = _response_result(
                    response=fallback,
                    matched=True,
                    intent_tag=fallback_intent,
                    confidence=None,
                    source="pattern_fallback",
                )
                return result if return_meta else result["response"]
            result = _response_result(
                response=UNKNOWN_RESPONSE,
                matched=False,
                intent_tag=None,
                confidence=None,
                source="unknown",
            )
            return result if return_meta else result["response"]

        # Pad sequence
        padded = pad_sequences(sequence, maxlen=max_len, padding="post")

        # Predict intent
        prediction = model.predict(padded, verbose=0)

        intent_index = np.argmax(prediction)

        confidence = prediction[0][intent_index]

        intent = label_encoder.inverse_transform([intent_index])[0]

        # If confidence is low, use fallback pattern matching.
        if confidence < 0.5:
            fallback, fallback_intent = pattern_fallback(user_input)
            if fallback:
                result = _response_result(
                    response=fallback,
                    matched=True,
                    intent_tag=fallback_intent,
                    confidence=confidence,
                    source="pattern_fallback",
                )
                return result if return_meta else result["response"]
            result = _response_result(
                response=UNKNOWN_RESPONSE,
                matched=False,
                intent_tag=None,
                confidence=confidence,
                source="low_confidence",
            )
            return result if return_meta else result["response"]

        # Fetch predicted intent (MongoDB first, local fallback second).
        intent_data = get_intent_by_tag(intent)

        if intent_data and "responses" in intent_data:
            result = _response_result(
                response=np.random.choice(intent_data["responses"]),
                matched=True,
                intent_tag=intent,
                confidence=confidence,
                source="model",
            )
            return result if return_meta else result["response"]

        fallback, fallback_intent = pattern_fallback(user_input)
        if fallback:
            result = _response_result(
                response=fallback,
                matched=True,
                intent_tag=fallback_intent,
                confidence=confidence,
                source="pattern_fallback",
            )
            return result if return_meta else result["response"]

        result = _response_result(
            response=UNKNOWN_RESPONSE,
            matched=False,
            intent_tag=intent,
            confidence=confidence,
            source="intent_missing",
        )
        return result if return_meta else result["response"]

    except Exception as e:
        print("Chatbot error:", e)

    result = _response_result(
        response=UNKNOWN_RESPONSE,
        matched=False,
        intent_tag=None,
        confidence=None,
        source="error",
    )
    return result if return_meta else result["response"]
