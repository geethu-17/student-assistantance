from pymongo import MongoClient
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")


def normalize_mongo_uri(uri):
    if not uri:
        return uri

    cleaned = uri.strip()

    # Fix accidental double slash in copied Atlas URI.
    cleaned = cleaned.replace(".net//", ".net/")

    # Remove angle brackets if pasted from docs template.
    cleaned = cleaned.replace("<", "").replace(">", "")

    return cleaned


MONGO_URI = normalize_mongo_uri(os.getenv("MONGO_URI"))
MONGO_URI_FALLBACK = normalize_mongo_uri(os.getenv("MONGO_URI_FALLBACK"))
MONGO_URI_LOCAL = normalize_mongo_uri(os.getenv("MONGO_URI_LOCAL"))
DB_NAME = os.getenv("MONGO_DB_NAME", "Student-chat-bot-data")
SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "15000"))
CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "10000"))
SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "10000"))

_db = None
_client = None
_active_uri_name = None


def get_db():
    global _db, _client, _active_uri_name

    if _db is not None:
        return _db

    uri_candidates = [
        ("MONGO_URI", MONGO_URI),
        ("MONGO_URI_FALLBACK", MONGO_URI_FALLBACK),
        ("MONGO_URI_LOCAL", MONGO_URI_LOCAL),
    ]
    uri_candidates = [(name, uri) for name, uri in uri_candidates if uri]

    if not uri_candidates:
        raise RuntimeError(
            "No Mongo URI configured. Set MONGO_URI in .env "
            "(optionally MONGO_URI_FALLBACK / MONGO_URI_LOCAL)."
        )

    errors = []

    for uri_name, uri in uri_candidates:
        # Try twice in case of transient network/DNS instability.
        for attempt in (1, 2):
            try:
                _client = MongoClient(
                    uri,
                    serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
                    connectTimeoutMS=CONNECT_TIMEOUT_MS,
                    socketTimeoutMS=SOCKET_TIMEOUT_MS,
                    retryReads=True,
                    retryWrites=True,
                )

                # Validate connection explicitly.
                _client.admin.command("ping")
                _db = _client[DB_NAME]
                _active_uri_name = uri_name
                print(f"[database] MongoDB connected successfully via {uri_name}")
                return _db
            except Exception as e:
                errors.append(f"{uri_name} (attempt {attempt}): {e}")
                time.sleep(0.5)

    message = " | ".join(errors)
    hint = ""
    if "ReplicaSetNoPrimary" in message or "No replica set members found yet" in message:
        hint = (
            " Atlas reachability issue: ensure Atlas Network Access allows your current IP, "
            "confirm Database Access credentials, and verify port 27017/TLS is not blocked "
            "by firewall/antivirus/VPN."
        )

    final_message = message + hint
    print("[database] MongoDB connection failed:", final_message)
    raise RuntimeError(final_message)


def check_mongo_connection():
    """Return (ok: bool, message: str) for quick diagnostics."""
    try:
        get_db()
        source = _active_uri_name or "unknown"
        return True, f"Connected to database '{DB_NAME}' via {source}"
    except Exception as e:
        return False, str(e)


class LazyCollection:
    def __init__(self, collection_name):
        self.collection_name = collection_name

    def _collection(self):
        return get_db()[self.collection_name]

    def __getattr__(self, attr):
        return getattr(self._collection(), attr)


# Collections
users_collection = LazyCollection("users")
admins_collection = LazyCollection("admins")
intents_collection = LazyCollection("intents")
chat_logs_collection = LazyCollection("chat_logs")
applications_collection = LazyCollection("applications")
academic_calendar_collection = LazyCollection("academic_calendar")
counseling_collection = LazyCollection("counseling_requests")
counseling_slots_collection = LazyCollection("counseling_slots")
faq_suggestion_state_collection = LazyCollection("faq_suggestion_state")
credit_requirements_collection = LazyCollection("credit_requirements")
student_credits_collection = LazyCollection("student_credits")
loan_assistance_collection = LazyCollection("loan_assistance")
programs_collection = LazyCollection("programs")
course_registration_collection = LazyCollection("course_registration_guidance")
fee_structure_collection = LazyCollection("fee_structure")
scholarships_collection = LazyCollection("scholarships")
hostel_info_collection = LazyCollection("hostel_info")
transport_schedules_collection = LazyCollection("transport_schedules")
campus_navigation_collection = LazyCollection("campus_navigation")
stress_resources_collection = LazyCollection("stress_resources")
admin_audit_logs_collection = LazyCollection("admin_audit_logs")
