from flask import Blueprint, request, jsonify, make_response
from bson import ObjectId
import bcrypt
import re
import os
import csv
import io
import json
import hashlib
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
from flask import g

from database import (
    admins_collection,
    intents_collection,
    users_collection,
    chat_logs_collection,
    counseling_collection,
    counseling_slots_collection,
    faq_suggestion_state_collection,
    applications_collection,
    programs_collection,
    course_registration_collection,
    academic_calendar_collection,
    credit_requirements_collection,
    student_credits_collection,
    fee_structure_collection,
    scholarships_collection,
    loan_assistance_collection,
    hostel_info_collection,
    transport_schedules_collection,
    campus_navigation_collection,
    stress_resources_collection,
    admin_audit_logs_collection,
)
from utils.admin_auth import require_admin_auth, create_admin_token, ADMIN_TOKEN_EXPIRES_SECONDS
from services.password_reset_delivery import send_password_reset_email, email_delivery_ready, send_smtp_test_email

admin_routes = Blueprint("admin_routes", __name__)
ADMIN_RESET_TOKEN_TTL_MINUTES = 20


def _hash_reset_token(raw_token):
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def _parse_pagination(default_limit=20, max_limit=200):
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    try:
        limit = int(request.args.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit

    page = max(page, 1)
    limit = max(1, min(limit, max_limit))
    skip = (page - 1) * limit

    return page, limit, skip


def _paginate_response(items, total, page, limit):
    pages = (total + limit - 1) // limit if total else 0
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
        },
    }


def _parse_string_list(values):
    if not isinstance(values, list):
        return []

    cleaned = []
    for item in values:
        text = (item or "").strip() if isinstance(item, str) else ""
        if text:
            cleaned.append(text)

    return cleaned


def _normalize_list_input(values):
    if isinstance(values, list):
        return _parse_string_list(values)
    if isinstance(values, str):
        raw = values.strip()
        if not raw:
            return []
        if "\n" in raw:
            parts = [line.strip() for line in raw.split("\n")]
        elif "|" in raw:
            parts = [part.strip() for part in raw.split("|")]
        else:
            parts = [part.strip() for part in raw.split(",")]
        return [p for p in parts if p]
    return []


def _admin_password_matches(admin_doc, password):
    stored = admin_doc.get("password")
    if stored is None:
        return False

    if isinstance(stored, bytes):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored)
        except Exception:
            return False

    if isinstance(stored, str) and stored.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False

    return stored == password


STOP_WORDS = {
    "the", "is", "a", "an", "and", "or", "to", "of", "for", "in", "on", "at",
    "with", "about", "can", "you", "i", "me", "my", "we", "our", "do", "does",
    "how", "what", "when", "where", "why", "please", "tell", "give", "want",
    "need", "help",
}


def _normalize_question(text):
    if not isinstance(text, str):
        return ""
    lowered = text.lower().strip()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _suggest_tag(question):
    words = [w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in STOP_WORDS]
    if not words:
        return "general_query"
    return "_".join(words[:3])


def _generate_response_hint(question):
    return f"Thank you for your question about '{question}'. We are updating this answer soon."


def _sanitize_tag(text):
    raw = _normalize_question(text)
    if not raw:
        return "general_query"
    parts = [p for p in raw.split(" ") if p and p not in STOP_WORDS]
    if not parts:
        parts = [p for p in raw.split(" ") if p]
    joined = "_".join(parts[:3]) if parts else "general_query"
    return joined[:60] or "general_query"


def _intent_tag_exists(tag):
    existing = intents_collection.find_one({
        "tag": {"$regex": f"^{re.escape(tag)}$", "$options": "i"}
    })
    return bool(existing)


def _resolve_unique_intent_tag(base_tag):
    normalized_base = _sanitize_tag(base_tag)
    if not _intent_tag_exists(normalized_base):
        return normalized_base

    version = 2
    while version <= 9999:
        candidate = f"{normalized_base}_v{version}"
        if not _intent_tag_exists(candidate):
            return candidate
        version += 1

    return f"{normalized_base}_{int(datetime.utcnow().timestamp())}"


def _is_valid_date_yyyy_mm_dd(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except Exception:
        return False


def _is_valid_time_hh_mm_24h(value):
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except Exception:
        return False


def _is_end_time_after_start(start_time, end_time):
    try:
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        return end_dt > start_dt
    except Exception:
        return False


def _slot_doc_to_response(slot_doc, source="slots"):
    return {
        "id": str(slot_doc.get("_id")),
        "date": slot_doc.get("date"),
        "start_time": slot_doc.get("start_time"),
        "end_time": slot_doc.get("end_time"),
        "mode": slot_doc.get("mode"),
        "counselor": slot_doc.get("counselor"),
        "is_active": slot_doc.get("is_active", True),
        "source": source,
    }


def _find_slot_by_id(slot_id):
    if not ObjectId.is_valid(str(slot_id)):
        return None, None
    oid = ObjectId(str(slot_id))

    slot_doc = counseling_slots_collection.find_one({"_id": oid})
    if slot_doc:
        return slot_doc, "slots"

    fallback_slot = counseling_collection.find_one({"_id": oid, "doc_type": "slot"})
    if fallback_slot:
        return fallback_slot, "fallback"

    return None, None


def _normalize_counselor_name(name):
    return (name or "Counselor").strip().lower()


def _time_to_minutes(hhmm):
    dt = datetime.strptime(hhmm, "%H:%M")
    return (dt.hour * 60) + dt.minute


def _times_overlap(start_a, end_a, start_b, end_b):
    a_start = _time_to_minutes(start_a)
    a_end = _time_to_minutes(end_a)
    b_start = _time_to_minutes(start_b)
    b_end = _time_to_minutes(end_b)
    return a_start < b_end and b_start < a_end


def _get_all_active_slots():
    slots = list(
        counseling_slots_collection.find(
            {"is_active": True},
            {"date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1, "is_active": 1},
        )
    )
    fallback_slots = list(
        counseling_collection.find(
            {"doc_type": "slot", "is_active": True},
            {"date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1, "is_active": 1},
        )
    )
    return slots + fallback_slots


def _has_counselor_slot_conflict(date, start_time, end_time, counselor, exclude_slot_id=None):
    target_counselor = _normalize_counselor_name(counselor)
    exclude_str = str(exclude_slot_id) if exclude_slot_id else None

    for slot in _get_all_active_slots():
        if exclude_str and str(slot.get("_id")) == exclude_str:
            continue
        if (slot.get("date") or "").strip() != date:
            continue
        if _normalize_counselor_name(slot.get("counselor")) != target_counselor:
            continue
        if _times_overlap(start_time, end_time, slot.get("start_time", "00:00"), slot.get("end_time", "00:00")):
            return True

    return False


def _has_counselor_booking_conflict(slot_doc, exclude_booking_id=None):
    if not slot_doc:
        return False

    date = (slot_doc.get("date") or "").strip()
    start_time = (slot_doc.get("start_time") or "").strip()
    end_time = (slot_doc.get("end_time") or "").strip()
    counselor = _normalize_counselor_name(slot_doc.get("counselor"))
    exclude_booking = str(exclude_booking_id) if exclude_booking_id else None

    scheduled_bookings = list(
        counseling_collection.find(
            {"status": "scheduled", "doc_type": {"$ne": "slot"}, "scheduled_slot_id": {"$ne": None}},
            {"scheduled_slot_id": 1},
        )
    )

    for booking in scheduled_bookings:
        if exclude_booking and str(booking.get("_id")) == exclude_booking:
            continue
        other_slot, _ = _find_slot_by_id(booking.get("scheduled_slot_id"))
        if not other_slot:
            continue
        if (other_slot.get("date") or "").strip() != date:
            continue
        if _normalize_counselor_name(other_slot.get("counselor")) != counselor:
            continue
        if _times_overlap(start_time, end_time, other_slot.get("start_time", "00:00"), other_slot.get("end_time", "00:00")):
            return True

    return False


MODULE_COLLECTIONS = {
    "applications": applications_collection,
    "programs": programs_collection,
    "course_registration_guidance": course_registration_collection,
    "academic_calendar": academic_calendar_collection,
    "credit_requirements": credit_requirements_collection,
    "student_credits": student_credits_collection,
    "fee_structure": fee_structure_collection,
    "scholarships": scholarships_collection,
    "loan_assistance": loan_assistance_collection,
    "hostel_info": hostel_info_collection,
    "transport_schedules": transport_schedules_collection,
    "campus_navigation": campus_navigation_collection,
    "stress_resources": stress_resources_collection,
}

MODULE_ARRAY_FIELDS = {
    "course_registration_guidance": {"steps", "required_documents", "contacts"},
    "loan_assistance": {"required_documents"},
    "hostel_info": {"facilities"},
    "transport_schedules": {"pickup_points"},
    "campus_navigation": {"route_steps"},
}

MODULE_NUMBER_FIELDS = {
    "programs": {"duration_years", "intake"},
    "credit_requirements": {"required_credits", "semester"},
    "student_credits": {"earned_credits", "semester"},
    "fee_structure": {"tuition_fee", "hostel_fee", "other_charges"},
    "hostel_info": {"capacity", "fee_per_year"},
    "campus_navigation": {"approx_minutes"},
}


def _module_collection_or_404(module_name):
    collection = MODULE_COLLECTIONS.get((module_name or "").strip())
    if not collection:
        return None
    return collection


def _serialize_doc(doc):
    if not doc:
        return doc
    data = dict(doc)
    if "_id" in data:
        data["id"] = str(data.pop("_id"))
    return data


def _build_module_search_query(search):
    search = (search or "").strip()
    if not search:
        return {}
    search_re = {"$regex": re.escape(search), "$options": "i"}
    return {
        "$or": [
            {"name": search_re},
            {"title": search_re},
            {"program": search_re},
            {"event": search_re},
            {"description": search_re},
            {"registration_number": search_re},
            {"application_id": search_re},
            {"route_name": search_re},
            {"hostel_name": search_re},
            {"student": search_re},
            {"from": search_re},
            {"to": search_re},
        ]
    }


def _normalize_import_value(module_name, field_name, value):
    if value is None:
        return ""

    if isinstance(value, str):
        value = value.strip()
    if value == "":
        return ""

    if field_name in MODULE_ARRAY_FIELDS.get(module_name, set()):
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return [v.strip() for v in str(value).split(",") if v.strip()]

    if field_name in MODULE_NUMBER_FIELDS.get(module_name, set()):
        try:
            as_number = float(value)
            return int(as_number) if as_number.is_integer() else as_number
        except Exception:
            return value

    return value


def _parse_uploaded_rows(upload):
    if not upload:
        raise ValueError("No file uploaded. Use form-data key: file")

    filename = (upload.filename or "").strip().lower()
    if not filename:
        raise ValueError("Uploaded file name is missing")

    try:
        raw_bytes = upload.read()
        if len(raw_bytes) > (10 * 1024 * 1024):
            raise ValueError("File is too large. Maximum supported size is 10 MB")
        text = raw_bytes.decode("utf-8-sig", errors="ignore")
    except Exception:
        raise ValueError("Failed to read uploaded file")

    try:
        if filename.endswith(".json"):
            parsed = json.loads(text or "[]")
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                raise ValueError("JSON must be an object or array of objects")
            return parsed
        if filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(text))
            return [dict(row) for row in reader]
        raise ValueError("Unsupported file type. Upload .csv or .json")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse file: {str(e)}")


def _admin_actor():
    admin = getattr(g, "admin", {}) or {}
    return (
        admin.get("username")
        or admin.get("email")
        or "admin"
    )


def _write_admin_audit(action, module_name, record_id=None, details=None):
    try:
        admin_audit_logs_collection.insert_one(
            {
                "admin": _admin_actor(),
                "action": action,
                "module": module_name,
                "record_id": record_id,
                "details": details or {},
                "timestamp": datetime.utcnow(),
            }
        )
    except Exception as e:
        # Audit logging should not break primary operation.
        print("[admin_audit] failed:", e)


def _safe_for_audit(value):
    if isinstance(value, bytes):
        return "<bytes>"
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_safe_for_audit(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_for_audit(v) for k, v in value.items() if str(k) != "password"}
    return value


def _build_change_diff(before_doc, after_doc):
    before = _safe_for_audit(before_doc or {})
    after = _safe_for_audit(after_doc or {})
    keys = set(before.keys()) | set(after.keys())
    keys.discard("password")
    keys.discard("updated_at")
    keys.discard("created_at")
    changed = {}
    for key in sorted(keys):
        if before.get(key) != after.get(key):
            changed[key] = {"before": before.get(key), "after": after.get(key)}
    return changed


# -------------------------
# Admin Login
# -------------------------
@admin_routes.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}

    username = (
        data.get("username")
        or data.get("identifier")
        or data.get("email")
        or ""
    ).strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Missing admin credentials"}), 400

    try:
        admin = admins_collection.find_one(
            {
                "$or": [
                    {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}},
                    {"email": {"$regex": f"^{re.escape(username)}$", "$options": "i"}},
                ]
            }
        )

        if not admin:
            return jsonify({"error": "Invalid admin credentials"}), 401

        if not _admin_password_matches(admin, password):
            return jsonify({"error": "Invalid admin credentials"}), 401

        admin_payload = {
            "username": admin.get("username"),
            "email": admin.get("email"),
            "role": "admin",
        }
        token = create_admin_token(admin_payload)

        return jsonify({
            "message": "Admin login successful",
            "admin": admin_payload,
            "token": token,
            "expires_in": ADMIN_TOKEN_EXPIRES_SECONDS,
        })
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Admin Forgot Password
# -------------------------
@admin_routes.route("/admin/forgot-password", methods=["POST"])
def admin_forgot_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        return jsonify({"error": "identifier is required"}), 400

    try:
        admin = admins_collection.find_one({
            "$or": [
                {"username": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
            ]
        })
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        reset_token = secrets.token_urlsafe(24)
        token_hash = _hash_reset_token(reset_token)
        expires_at = datetime.utcnow() + timedelta(minutes=ADMIN_RESET_TOKEN_TTL_MINUTES)

        admins_collection.update_one(
            {"_id": admin["_id"]},
            {"$set": {
                "password_reset_token_hash": token_hash,
                "password_reset_token_expires_at": expires_at,
                "password_reset_requested_at": datetime.utcnow(),
            }}
        )

        delivery = send_password_reset_email(
            recipient_email=admin.get("email"),
            reset_token=reset_token,
            expires_in_minutes=ADMIN_RESET_TOKEN_TTL_MINUTES,
            audience="admin",
        )

        if delivery.get("sent"):
            return jsonify({
                "message": "Admin reset token sent to registered email",
                "identifier": identifier,
                "delivery": {"sent": True, "channel": "email"},
                "expires_in_minutes": ADMIN_RESET_TOKEN_TTL_MINUTES,
            }), 200

        return jsonify({
            "message": "Admin reset token generated (email delivery unavailable)",
            "identifier": identifier,
            "reset_token": reset_token,
            "expires_in_minutes": ADMIN_RESET_TOKEN_TTL_MINUTES,
            "delivery": {
                "sent": False,
                "channel": "email",
                "reason": delivery.get("reason"),
                "details": delivery.get("message"),
                "email_configured": email_delivery_ready(),
            },
        }), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Admin Reset Password
# -------------------------
@admin_routes.route("/admin/reset-password", methods=["POST"])
def admin_reset_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    reset_token = (data.get("reset_token") or "").strip()
    new_password = data.get("new_password") or ""

    if not identifier or not reset_token or not new_password:
        return jsonify({"error": "identifier, reset_token and new_password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "new_password must be at least 6 characters"}), 400

    try:
        admin = admins_collection.find_one({
            "$or": [
                {"username": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
            ]
        })
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        expected_hash = admin.get("password_reset_token_hash")
        expires_at = admin.get("password_reset_token_expires_at")
        if not expected_hash or not expires_at:
            return jsonify({"error": "No active reset token. Request forgot password first"}), 400
        if datetime.utcnow() > expires_at:
            return jsonify({"error": "Reset token expired. Request a new one"}), 400
        if _hash_reset_token(reset_token) != expected_hash:
            return jsonify({"error": "Invalid reset token"}), 401

        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        admins_collection.update_one(
            {"_id": admin["_id"]},
            {"$set": {"password": hashed_password},
             "$unset": {
                 "password_reset_token_hash": "",
                 "password_reset_token_expires_at": "",
                 "password_reset_requested_at": "",
             }}
        )

        return jsonify({"message": "Admin password reset successful"}), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Dashboard Stats
# -------------------------
@admin_routes.route("/admin/dashboard", methods=["GET"])
@require_admin_auth
def dashboard_stats():
    try:
        total_chats = chat_logs_collection.count_documents({})
        total_users = users_collection.count_documents({})
        negative_sentiment = chat_logs_collection.count_documents({"sentiment": "negative"})

        top_questions_cursor = chat_logs_collection.aggregate([
            {"$match": {"message": {"$type": "string", "$ne": ""}}},
            {
                "$project": {
                    "question": {"$trim": {"input": {"$toLower": "$message"}}},
                    "timestamp": 1,
                }
            },
            {"$match": {"question": {"$ne": ""}}},
            {
                "$group": {
                    "_id": "$question",
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$timestamp"},
                }
            },
            {"$sort": {"count": -1, "last_seen": -1}},
            {"$limit": 10},
        ])
        top_questions = [
            {"question": row.get("_id"), "count": row.get("count", 0), "last_seen": row.get("last_seen")}
            for row in top_questions_cursor
            if row.get("_id")
        ]

        unmatched_cursor = chat_logs_collection.aggregate([
            {
                "$match": {
                    "$or": [
                        {"matched": False},
                        {"match_source": {"$in": ["unknown", "low_confidence", "intent_missing"]}},
                    ]
                }
            },
            {"$match": {"message": {"$type": "string", "$ne": ""}}},
            {
                "$project": {
                    "question": {"$trim": {"input": {"$toLower": "$message"}}},
                    "timestamp": 1,
                }
            },
            {"$match": {"question": {"$ne": ""}}},
            {
                "$group": {
                    "_id": "$question",
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$timestamp"},
                }
            },
            {"$sort": {"count": -1, "last_seen": -1}},
            {"$limit": 10},
        ])
        unmatched_questions = [
            {"question": row.get("_id"), "count": row.get("count", 0), "last_seen": row.get("last_seen")}
            for row in unmatched_cursor
            if row.get("_id")
        ]

        return jsonify({
            "total_chats": total_chats,
            "users": total_users,
            "negative_sentiment": negative_sentiment,
            "top_questions": top_questions,
            "unmatched_questions": unmatched_questions,
        })
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/faq-suggestions", methods=["GET"])
@require_admin_auth
def get_faq_suggestions():
    try:
        try:
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        try:
            min_count = int(request.args.get("min_count", 2))
        except (TypeError, ValueError):
            min_count = 2
        min_count = max(1, min(min_count, 20))
        include_handled = str(request.args.get("include_handled", "false")).lower() == "true"

        handled_rows = list(
            faq_suggestion_state_collection.find(
                {"handled": True},
                {"_id": 0, "normalized_question": 1},
            )
        )
        handled_questions = {
            (row.get("normalized_question") or "").strip()
            for row in handled_rows
            if row.get("normalized_question")
        }

        unmatched_query = {
            "$or": [
                {"matched": False},
                {"match_source": {"$in": ["unknown", "low_confidence", "intent_missing", "error"]}},
                {"response": {"$regex": "^\\s*sorry, i didn't understand your question\\.?\\s*$", "$options": "i"}},
            ]
        }

        raw_rows = list(
            chat_logs_collection.find(
                unmatched_query,
                {"_id": 0, "message": 1, "timestamp": 1},
            ).sort("timestamp", -1).limit(5000)
        )

        grouped = defaultdict(lambda: {"count": 0, "last_seen": None, "variants": defaultdict(int)})

        for row in raw_rows:
            message = (row.get("message") or "").strip()
            if not message:
                continue
            normalized = _normalize_question(message)
            if not normalized:
                continue
            if not include_handled and normalized in handled_questions:
                continue
            entry = grouped[normalized]
            entry["count"] += 1
            entry["variants"][message] += 1
            ts = row.get("timestamp")
            if ts and (entry["last_seen"] is None or ts > entry["last_seen"]):
                entry["last_seen"] = ts

        suggestions = []
        for normalized, info in grouped.items():
            if info["count"] < min_count:
                continue
            sorted_variants = sorted(info["variants"].items(), key=lambda x: x[1], reverse=True)
            top_variants = [v for v, _ in sorted_variants[:4]]
            primary = top_variants[0] if top_variants else normalized
            suggestions.append({
                "question": primary,
                "normalized_question": normalized,
                "count": info["count"],
                "last_seen": info["last_seen"],
                "suggested_tag": _suggest_tag(normalized),
                "suggested_patterns": top_variants if top_variants else [primary],
                "suggested_responses": [_generate_response_hint(primary)],
            })

        suggestions.sort(key=lambda x: (x["count"], x["last_seen"] or 0), reverse=True)

        return jsonify({
            "items": suggestions[:limit],
            "meta": {
                "limit": limit,
                "min_count": min_count,
                "include_handled": include_handled,
                "source_rows": len(raw_rows),
                "groups": len(grouped),
                "handled_groups": len(handled_questions),
            }
        })
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/faq-suggestions/create-intent", methods=["POST"])
@require_admin_auth
def create_intent_from_suggestion():
    data = request.get_json(silent=True) or {}

    question = (data.get("question") or "").strip()
    normalized_question = _normalize_question(data.get("normalized_question") or question)
    requested_tag = (data.get("suggested_tag") or data.get("tag") or "").strip()
    patterns = _parse_string_list(data.get("suggested_patterns", data.get("patterns", [])))
    responses = _parse_string_list(data.get("suggested_responses", data.get("responses", [])))

    if not normalized_question:
        return jsonify({"error": "Question is required"}), 400

    if not patterns:
        patterns = [question or normalized_question]

    if not responses:
        responses = [_generate_response_hint(question or normalized_question)]

    try:
        final_tag = _resolve_unique_intent_tag(requested_tag or question or normalized_question)

        intent = {
            "tag": final_tag,
            "patterns": patterns,
            "responses": responses,
        }
        intents_collection.insert_one(intent)
        _write_admin_audit(
            action="create",
            module_name="intents",
            record_id=final_tag,
            details={
                "source": "faq_suggestion",
                "normalized_question": normalized_question,
            },
        )

        faq_suggestion_state_collection.update_one(
            {"normalized_question": normalized_question},
            {
                "$set": {
                    "normalized_question": normalized_question,
                    "question": question or normalized_question,
                    "handled": True,
                    "handled_at": datetime.utcnow(),
                    "created_intent_tag": final_tag,
                }
            },
            upsert=True,
        )

        return jsonify({
            "message": "Intent created from suggestion successfully",
            "intent": intent,
            "handled": True,
        }), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/counseling-slots", methods=["GET"])
@require_admin_auth
def admin_get_counseling_slots():
    try:
        date_filter = (request.args.get("date") or "").strip()
        include_inactive = str(request.args.get("include_inactive", "false")).lower() == "true"
        query = {}
        if not include_inactive:
            query["is_active"] = True
        if date_filter:
            query["date"] = date_filter

        slots_primary = list(
            counseling_slots_collection.find(
                query,
                {"date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1, "is_active": 1},
            ).sort("date", 1).sort("start_time", 1)
        )
        fallback_query = {"doc_type": "slot"}
        if not include_inactive:
            fallback_query["is_active"] = True
        if date_filter:
            fallback_query["date"] = date_filter
        slots_fallback = list(
            counseling_collection.find(
                fallback_query,
                {"date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1, "is_active": 1},
            ).sort("date", 1).sort("start_time", 1)
        )

        slots = []
        slots.extend([_slot_doc_to_response(slot, source="slots") for slot in slots_primary])
        slots.extend([_slot_doc_to_response(slot, source="fallback") for slot in slots_fallback])

        return jsonify({"items": slots, "include_inactive": include_inactive})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/counseling-slots", methods=["POST"])
@require_admin_auth
def admin_create_counseling_slot():
    data = request.get_json(silent=True) or {}

    date = (data.get("date") or "").strip()
    start_time = (data.get("start_time") or "").strip()
    end_time = (data.get("end_time") or "").strip()
    counselor = (data.get("counselor") or "").strip()
    mode = (data.get("mode") or "in_person").strip().lower()

    if not date or not start_time or not end_time:
        return jsonify({"error": "date, start_time and end_time are required"}), 400

    if not _is_valid_date_yyyy_mm_dd(date):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD (example: 2026-03-20)"}), 400

    if not _is_valid_time_hh_mm_24h(start_time) or not _is_valid_time_hh_mm_24h(end_time):
        return jsonify({"error": "Invalid time format. Use HH:MM in 24-hour format (example: 14:30)"}), 400

    if not _is_end_time_after_start(start_time, end_time):
        return jsonify({"error": "end_time must be later than start_time"}), 400

    if mode not in {"in_person", "online"}:
        return jsonify({"error": "mode must be in_person or online"}), 400

    if _has_counselor_slot_conflict(date, start_time, end_time, counselor or "Counselor"):
        return jsonify({"error": "Conflict: counselor already has a slot in this time range"}), 409

    slot_doc = {
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "counselor": counselor or "Counselor",
        "mode": mode,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }

    try:
        try:
            result = counseling_slots_collection.insert_one(slot_doc)
            slot_doc["id"] = str(result.inserted_id)
            slot_doc["source"] = "slots"
            _write_admin_audit(
                action="create",
                module_name="counseling_slots",
                record_id=str(result.inserted_id),
                details={"fields": ["date", "start_time", "end_time", "counselor", "mode"]},
            )
            return jsonify({"message": "Counseling slot created", "slot": slot_doc}), 201
        except Exception:
            fallback_doc = {
                **slot_doc,
                "doc_type": "slot",
            }
            fallback_result = counseling_collection.insert_one(fallback_doc)
            fallback_doc["id"] = str(fallback_result.inserted_id)
            fallback_doc["source"] = "fallback"
            _write_admin_audit(
                action="create",
                module_name="counseling_slots",
                record_id=str(fallback_result.inserted_id),
                details={"source": "fallback", "fields": ["date", "start_time", "end_time", "counselor", "mode"]},
            )
            return jsonify({
                "message": "Counseling slot created (fallback store)",
                "slot": fallback_doc,
            }), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/counseling-slots/<slot_id>", methods=["DELETE"])
@require_admin_auth
def admin_delete_counseling_slot(slot_id):
    if not ObjectId.is_valid(slot_id):
        return jsonify({"error": "Invalid slot id"}), 400

    try:
        result = counseling_slots_collection.update_one(
            {"_id": ObjectId(slot_id)},
            {"$set": {"is_active": False}},
        )
        if result.matched_count == 0:
            fallback_result = counseling_collection.update_one(
                {"_id": ObjectId(slot_id), "doc_type": "slot"},
                {"$set": {"is_active": False}},
            )
            if fallback_result.matched_count == 0:
                return jsonify({"error": "Slot not found"}), 404
        _write_admin_audit(
            action="delete",
            module_name="counseling_slots",
            record_id=slot_id,
            details={"deactivated": True},
        )
        return jsonify({"message": "Slot deactivated successfully"})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/counseling-bookings", methods=["GET"])
@require_admin_auth
def admin_get_counseling_bookings():
    try:
        page, limit, skip = _parse_pagination(default_limit=20, max_limit=100)
        search = (request.args.get("search") or "").strip()
        status = (request.args.get("status") or "").strip().lower()

        query = {"doc_type": {"$ne": "slot"}}
        if status:
            query["status"] = status

        if search:
            search_re = {"$regex": re.escape(search), "$options": "i"}
            query["$or"] = [
                {"student": search_re},
                {"message": search_re},
            ]

        total = counseling_collection.count_documents(query)
        bookings = list(
            counseling_collection.find(
                query,
                {"student": 1, "message": 1, "preferred_date": 1, "status": 1, "scheduled_slot_id": 1, "updated_at": 1, "created_at": 1},
            ).sort("created_at", -1).skip(skip).limit(limit)
        )

        for booking in bookings:
            booking["id"] = str(booking.pop("_id"))
            slot_id = booking.get("scheduled_slot_id")
            booking["scheduled_slot_id"] = str(slot_id) if slot_id else None
            if slot_id:
                slot_doc, slot_source = _find_slot_by_id(slot_id)
                if slot_doc:
                    booking["scheduled_slot"] = _slot_doc_to_response(slot_doc, source=slot_source or "slots")

        return jsonify(_paginate_response(bookings, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/counseling-bookings/<booking_id>/status", methods=["PUT"])
@require_admin_auth
def admin_update_counseling_booking_status(booking_id):
    if not ObjectId.is_valid(booking_id):
        return jsonify({"error": "Invalid booking id"}), 400

    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    slot_id = (data.get("slot_id") or "").strip()

    allowed = {"pending", "in_review", "scheduled", "completed", "rejected"}
    if status not in allowed:
        return jsonify({"error": f"status must be one of: {', '.join(sorted(allowed))}"}), 400

    booking_obj_id = ObjectId(booking_id)
    booking = counseling_collection.find_one({"_id": booking_obj_id, "doc_type": {"$ne": "slot"}})
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    update_data = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }

    if slot_id:
        if not ObjectId.is_valid(slot_id):
            return jsonify({"error": "Invalid slot_id"}), 400
        slot_obj_id = ObjectId(slot_id)
        slot_doc, _ = _find_slot_by_id(slot_obj_id)
        if not slot_doc:
            return jsonify({"error": "Selected slot not found or inactive"}), 404
        if slot_doc.get("is_active") is False:
            return jsonify({"error": "Selected slot is inactive"}), 409

        conflict = counseling_collection.find_one({
            "_id": {"$ne": booking_obj_id},
            "scheduled_slot_id": slot_obj_id,
            "status": "scheduled",
            "doc_type": {"$ne": "slot"},
        })
        if conflict:
            return jsonify({"error": "Selected slot is already assigned to another scheduled booking"}), 409

        if _has_counselor_booking_conflict(slot_doc, exclude_booking_id=booking_obj_id):
            return jsonify({"error": "Conflict: counselor already has another student scheduled in this time range"}), 409

        update_data["scheduled_slot_id"] = slot_obj_id
    elif status == "scheduled":
        return jsonify({"error": "slot_id is required when status is scheduled"}), 400
    elif status != "scheduled":
        update_data["scheduled_slot_id"] = None

    try:
        result = counseling_collection.update_one(
            {"_id": booking_obj_id},
            {"$set": update_data},
        )
        _write_admin_audit(
            action="update",
            module_name="counseling_bookings",
            record_id=booking_id,
            details={"fields": list(update_data.keys()), "status": status},
        )
        return jsonify({"message": "Booking status updated successfully"})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Chat Logs
# -------------------------
@admin_routes.route("/admin/chat-logs", methods=["GET"])
@require_admin_auth
def get_chat_logs():
    try:
        page, limit, skip = _parse_pagination(default_limit=25, max_limit=200)
        search = (request.args.get("search") or "").strip()

        query = {}
        if search:
            query = {
                "$or": [
                    {"user": {"$regex": re.escape(search), "$options": "i"}},
                    {"message": {"$regex": re.escape(search), "$options": "i"}},
                    {"response": {"$regex": re.escape(search), "$options": "i"}},
                ]
            }

        total = chat_logs_collection.count_documents(query)
        logs = list(
            chat_logs_collection.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
        )

        return jsonify(_paginate_response(logs, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Users
# -------------------------
@admin_routes.route("/admin/users", methods=["GET"])
@require_admin_auth
def get_users():
    try:
        page, limit, skip = _parse_pagination(default_limit=20, max_limit=100)
        search = (request.args.get("search") or "").strip()

        query = {}
        if search:
            search_re = {"$regex": re.escape(search), "$options": "i"}
            query = {
                "$or": [
                    {"name": search_re},
                    {"email": search_re},
                    {"registration_number": search_re},
                ]
            }

        total = users_collection.count_documents(query)
        users = list(
            users_collection.find(
                query,
                {"name": 1, "email": 1, "registration_number": 1, "role": 1},
            ).sort("name", 1).skip(skip).limit(limit)
        )

        for user in users:
            user["id"] = str(user.pop("_id"))

        return jsonify(_paginate_response(users, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/users/export", methods=["GET"])
@require_admin_auth
def export_users():
    export_format = (request.args.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "json"}:
        return jsonify({"error": "format must be csv or json"}), 400

    search = (request.args.get("search") or "").strip()
    query = {}
    if search:
        search_re = {"$regex": re.escape(search), "$options": "i"}
        query = {
            "$or": [
                {"name": search_re},
                {"email": search_re},
                {"registration_number": search_re},
            ]
        }

    try:
        rows = list(
            users_collection.find(query, {"password": 0}).sort("_id", -1)
        )
        items = [_serialize_doc(row) for row in rows]
        _write_admin_audit(
            action="export",
            module_name="users",
            details={"format": export_format, "count": len(items), "search": search},
        )
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if export_format == "json":
            payload = json.dumps(items, ensure_ascii=False, default=str, indent=2)
            response = make_response(payload)
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename=users_{timestamp}.json"
            return response

        fields = sorted({k for item in items for k in item.keys()}, key=lambda k: (k != "id", k))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow(item)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename=users_{timestamp}.csv"
        return response
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/users/import", methods=["POST"])
@require_admin_auth
def import_users():
    try:
        rows = _parse_uploaded_rows(request.files.get("file"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    imported = 0
    updated = 0
    skipped = 0

    try:
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue

            email = (str(row.get("email") or "")).strip().lower()
            name = (str(row.get("name") or "")).strip()
            registration_number = (str(row.get("registration_number") or "")).strip()
            role = (str(row.get("role") or "student")).strip() or "student"
            plain_password = str(row.get("password") or "").strip()

            if not email or not name:
                skipped += 1
                continue

            hashed_password = bcrypt.hashpw(
                (plain_password or "ChangeMe@123").encode("utf-8"),
                bcrypt.gensalt(),
            )

            doc = {
                "name": name,
                "email": email,
                "registration_number": registration_number or None,
                "role": role,
                "password": hashed_password,
                "updated_at": datetime.utcnow(),
            }

            existing = users_collection.find_one(
                {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
                {"_id": 1},
            )
            if existing:
                users_collection.update_one({"_id": existing["_id"]}, {"$set": doc})
                updated += 1
            else:
                doc["created_at"] = datetime.utcnow()
                users_collection.insert_one(doc)
                imported += 1

        _write_admin_audit(
            action="import",
            module_name="users",
            details={
                "attempted_count": len(rows),
                "imported_count": imported,
                "updated_count": updated,
                "skipped_count": skipped,
            },
        )
        return jsonify(
            {
                "message": "Users import completed",
                "imported_count": imported,
                "updated_count": updated,
                "skipped_count": skipped,
                "attempted_count": len(rows),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/delete-user/<user_id>", methods=["DELETE"])
@admin_routes.route("/admin/users/<user_id>", methods=["DELETE"])
@require_admin_auth
def delete_user(user_id):
    user_id = (user_id or "").strip()
    if not user_id:
        return jsonify({"error": "User id is required"}), 400

    try:
        if ObjectId.is_valid(user_id):
            query = {"_id": ObjectId(user_id)}
        else:
            query = {"email": {"$regex": f"^{re.escape(user_id)}$", "$options": "i"}}

        before_doc = users_collection.find_one(query, {"password": 0})
        result = users_collection.delete_one(query)

        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404
        _write_admin_audit(
            action="delete",
            module_name="users",
            record_id=user_id,
            details={"deleted_snapshot": _safe_for_audit(_serialize_doc(before_doc) if before_doc else {})},
        )

        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Add Intent
# -------------------------
@admin_routes.route("/admin/add-intent", methods=["POST"])
@admin_routes.route("/admin/intents", methods=["POST"])
@require_admin_auth
def add_intent():
    data = request.get_json(silent=True) or {}

    tag = (data.get("tag") or "").strip()
    patterns = _parse_string_list(data.get("patterns", []))
    responses = _parse_string_list(data.get("responses", []))

    if not tag:
        return jsonify({"error": "Intent tag is required"}), 400

    if not patterns:
        return jsonify({"error": "At least one pattern is required"}), 400

    if not responses:
        return jsonify({"error": "At least one response is required"}), 400

    try:
        existing = intents_collection.find_one({"tag": {"$regex": f"^{re.escape(tag)}$", "$options": "i"}})
        if existing:
            return jsonify({"error": "Intent tag already exists"}), 409

        intent = {"tag": tag, "patterns": patterns, "responses": responses}
        intents_collection.insert_one(intent)
        _write_admin_audit(
            action="create",
            module_name="intents",
            record_id=tag,
            details={"fields": ["tag", "patterns", "responses"]},
        )
        return jsonify({"message": "Intent added successfully", "intent": intent}), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Get All Intents
# -------------------------
@admin_routes.route("/admin/intents", methods=["GET"])
@require_admin_auth
def get_all_intents():
    try:
        page, limit, skip = _parse_pagination(default_limit=20, max_limit=100)
        search = (request.args.get("search") or "").strip()

        query = {}
        if search:
            query = {"tag": {"$regex": re.escape(search), "$options": "i"}}

        total = intents_collection.count_documents(query)
        intents = list(
            intents_collection.find(query, {"_id": 0}).sort("tag", 1).skip(skip).limit(limit)
        )

        return jsonify(_paginate_response(intents, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Update Intent
# -------------------------
@admin_routes.route("/admin/update-intent/<tag>", methods=["PUT"])
@admin_routes.route("/admin/intents/<tag>", methods=["PUT"])
@require_admin_auth
def update_intent(tag):
    data = request.get_json(silent=True) or {}

    target_tag = (tag or "").strip()
    new_tag = (data.get("tag") or target_tag).strip()
    patterns = _parse_string_list(data.get("patterns", []))
    responses = _parse_string_list(data.get("responses", []))

    if not target_tag:
        return jsonify({"error": "Intent tag is required"}), 400

    if not new_tag:
        return jsonify({"error": "Updated intent tag is required"}), 400

    if not patterns:
        return jsonify({"error": "At least one pattern is required"}), 400

    if not responses:
        return jsonify({"error": "At least one response is required"}), 400

    try:
        before_doc = intents_collection.find_one({"tag": target_tag})
        if new_tag.lower() != target_tag.lower():
            existing = intents_collection.find_one({"tag": {"$regex": f"^{re.escape(new_tag)}$", "$options": "i"}})
            if existing:
                return jsonify({"error": "Intent tag already exists"}), 409

        result = intents_collection.update_one(
            {"tag": target_tag},
            {"$set": {"tag": new_tag, "patterns": patterns, "responses": responses}},
        )

        if result.matched_count == 0:
            return jsonify({"error": "Intent not found"}), 404
        after_doc = intents_collection.find_one({"tag": new_tag})
        changed = _build_change_diff(before_doc, after_doc)
        _write_admin_audit(
            action="update",
            module_name="intents",
            record_id=target_tag,
            details={
                "updated_tag": new_tag,
                "fields": ["tag", "patterns", "responses"],
                "changed_fields": changed,
            },
        )

        return jsonify({
            "message": "Intent updated successfully",
            "intent": {"tag": new_tag, "patterns": patterns, "responses": responses},
        })
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Delete Intent
# -------------------------
@admin_routes.route("/admin/delete-intent/<tag>", methods=["DELETE"])
@admin_routes.route("/admin/intents/<tag>", methods=["DELETE"])
@require_admin_auth
def delete_intent(tag):
    tag = (tag or "").strip()
    if not tag:
        return jsonify({"error": "Intent tag is required"}), 400

    try:
        result = intents_collection.delete_one({"tag": tag})

        if result.deleted_count == 0:
            return jsonify({"error": "Intent not found"}), 404
        _write_admin_audit(
            action="delete",
            module_name="intents",
            record_id=tag,
            details={},
        )

        return jsonify({"message": "Intent deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/intents/export", methods=["GET"])
@require_admin_auth
def export_intents():
    export_format = (request.args.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "json"}:
        return jsonify({"error": "format must be csv or json"}), 400

    search = (request.args.get("search") or "").strip()
    query = {}
    if search:
        query = {"tag": {"$regex": re.escape(search), "$options": "i"}}

    try:
        rows = list(intents_collection.find(query, {"_id": 0}).sort("tag", 1))
        _write_admin_audit(
            action="export",
            module_name="intents",
            details={"format": export_format, "count": len(rows), "search": search},
        )
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if export_format == "json":
            payload = json.dumps(rows, ensure_ascii=False, default=str, indent=2)
            response = make_response(payload)
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename=intents_{timestamp}.json"
            return response

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["tag", "patterns", "responses"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "tag": row.get("tag", ""),
                    "patterns": " | ".join(row.get("patterns") or []),
                    "responses": " | ".join(row.get("responses") or []),
                }
            )

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename=intents_{timestamp}.csv"
        return response
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/intents/import", methods=["POST"])
@require_admin_auth
def import_intents():
    try:
        rows = _parse_uploaded_rows(request.files.get("file"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    imported = 0
    updated = 0
    skipped = 0

    try:
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            tag = (row.get("tag") or row.get("intent") or "").strip()
            patterns = _normalize_list_input(row.get("patterns") or row.get("text") or [])
            responses = _normalize_list_input(row.get("responses") or [])

            if not tag or not patterns or not responses:
                skipped += 1
                continue

            existing = intents_collection.find_one({"tag": {"$regex": f"^{re.escape(tag)}$", "$options": "i"}})
            doc = {"tag": tag, "patterns": patterns, "responses": responses}
            if existing:
                intents_collection.update_one({"_id": existing["_id"]}, {"$set": doc})
                updated += 1
            else:
                intents_collection.insert_one(doc)
                imported += 1

        _write_admin_audit(
            action="import",
            module_name="intents",
            details={
                "attempted_count": len(rows),
                "imported_count": imported,
                "updated_count": updated,
                "skipped_count": skipped,
            },
        )
        return jsonify(
            {
                "message": "Intents import completed",
                "imported_count": imported,
                "updated_count": updated,
                "skipped_count": skipped,
                "attempted_count": len(rows),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Functional Module Data CRUD
# -------------------------
@admin_routes.route("/admin/module-data/<module_name>", methods=["GET"])
@require_admin_auth
def get_module_data(module_name):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404

    try:
        page, limit, skip = _parse_pagination(default_limit=20, max_limit=200)
        search = (request.args.get("search") or "").strip()
        query = _build_module_search_query(search)

        total = collection.count_documents(query)
        rows = list(collection.find(query).sort("_id", -1).skip(skip).limit(limit))
        items = [_serialize_doc(row) for row in rows]
        return jsonify(_paginate_response(items, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/module-data/<module_name>/export", methods=["GET"])
@require_admin_auth
def export_module_data(module_name):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404

    export_format = (request.args.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "json"}:
        return jsonify({"error": "format must be csv or json"}), 400

    search = (request.args.get("search") or "").strip()
    query = _build_module_search_query(search)

    try:
        rows = list(collection.find(query).sort("_id", -1))
        items = [_serialize_doc(row) for row in rows]
        _write_admin_audit(
            action="export",
            module_name=module_name,
            details={"format": export_format, "count": len(items), "search": search},
        )

        safe_module_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", module_name)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if export_format == "json":
            payload = json.dumps(items, ensure_ascii=False, default=str, indent=2)
            response = make_response(payload)
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename={safe_module_name}_{timestamp}.json"
            return response

        # CSV export
        all_fields = set()
        for item in items:
            all_fields.update(item.keys())
        fieldnames = sorted(all_fields, key=lambda k: (k != "id", k))

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = {}
            for key in fieldnames:
                value = item.get(key)
                if isinstance(value, list):
                    row[key] = ", ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    row[key] = json.dumps(value, ensure_ascii=False, default=str)
                else:
                    row[key] = value
            writer.writerow(row)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename={safe_module_name}_{timestamp}.csv"
        return response
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/module-data/<module_name>/import", methods=["POST"])
@require_admin_auth
def import_module_data(module_name):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404

    upload = request.files.get("file")
    if not upload:
        return jsonify({"error": "No file uploaded. Use form-data key: file"}), 400

    filename = (upload.filename or "").strip().lower()
    if not filename:
        return jsonify({"error": "Uploaded file name is missing"}), 400

    try:
        raw_bytes = upload.read()
        text = raw_bytes.decode("utf-8-sig", errors="ignore")
    except Exception:
        return jsonify({"error": "Failed to read uploaded file"}), 400

    rows = []
    try:
        if filename.endswith(".json"):
            parsed = json.loads(text or "[]")
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                return jsonify({"error": "JSON must be an object or array of objects"}), 400
            rows = parsed
        elif filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(row) for row in reader]
        else:
            return jsonify({"error": "Unsupported file type. Upload .csv or .json"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400

    cleaned_docs = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned = {}
        for key, value in row.items():
            field = (key or "").strip()
            if not field or field in {"_id", "id"}:
                continue
            normalized = _normalize_import_value(module_name, field, value)
            if normalized == "":
                continue
            cleaned[field] = normalized
        if cleaned:
            cleaned["updated_at"] = datetime.utcnow()
            cleaned.setdefault("created_at", datetime.utcnow())
            cleaned_docs.append(cleaned)

    if not cleaned_docs:
        return jsonify({"error": "No valid rows found in uploaded file"}), 400

    try:
        result = collection.insert_many(cleaned_docs, ordered=False)
        _write_admin_audit(
            action="import",
            module_name=module_name,
            details={
                "attempted_count": len(cleaned_docs),
                "imported_count": len(result.inserted_ids),
            },
        )
        return jsonify(
            {
                "message": "File imported successfully",
                "imported_count": len(result.inserted_ids),
                "attempted_count": len(cleaned_docs),
                "module": module_name,
            }
        ), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/module-data/<module_name>", methods=["POST"])
@require_admin_auth
def create_module_data(module_name):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Request body must be a non-empty JSON object"}), 400

    payload.pop("_id", None)
    payload.pop("id", None)
    payload["updated_at"] = datetime.utcnow()
    payload.setdefault("created_at", datetime.utcnow())

    try:
        result = collection.insert_one(payload)
        created = collection.find_one({"_id": result.inserted_id})
        _write_admin_audit(
            action="create",
            module_name=module_name,
            record_id=str(result.inserted_id),
            details={"fields": list(payload.keys()), "after_snapshot": _safe_for_audit(_serialize_doc(created) or {})},
        )
        return jsonify({"message": "Record created successfully", "item": _serialize_doc(created)}), 201
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/module-data/<module_name>/<record_id>", methods=["PUT"])
@require_admin_auth
def update_module_data(module_name, record_id):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404
    if not ObjectId.is_valid(record_id):
        return jsonify({"error": "Invalid record id"}), 400

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Request body must be a non-empty JSON object"}), 400

    payload.pop("_id", None)
    payload.pop("id", None)
    payload["updated_at"] = datetime.utcnow()

    try:
        before_doc = collection.find_one({"_id": ObjectId(record_id)})
        result = collection.update_one({"_id": ObjectId(record_id)}, {"$set": payload})
        if result.matched_count == 0:
            return jsonify({"error": "Record not found"}), 404
        updated = collection.find_one({"_id": ObjectId(record_id)})
        changed = _build_change_diff(before_doc, updated)
        _write_admin_audit(
            action="update",
            module_name=module_name,
            record_id=record_id,
            details={
                "fields": list(payload.keys()),
                "changed_fields": changed,
                "before_snapshot": _safe_for_audit(_serialize_doc(before_doc) if before_doc else {}),
                "after_snapshot": _safe_for_audit(_serialize_doc(updated) if updated else {}),
            },
        )
        return jsonify({"message": "Record updated successfully", "item": _serialize_doc(updated)})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/module-data/<module_name>/<record_id>", methods=["DELETE"])
@require_admin_auth
def delete_module_data(module_name, record_id):
    collection = _module_collection_or_404(module_name)
    if not collection:
        return jsonify({"error": f"Unknown module collection: {module_name}"}), 404
    if not ObjectId.is_valid(record_id):
        return jsonify({"error": "Invalid record id"}), 400

    try:
        before_doc = collection.find_one({"_id": ObjectId(record_id)})
        result = collection.delete_one({"_id": ObjectId(record_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Record not found"}), 404
        _write_admin_audit(
            action="delete",
            module_name=module_name,
            record_id=record_id,
            details={"deleted_snapshot": _safe_for_audit(_serialize_doc(before_doc) if before_doc else {})},
        )
        return jsonify({"message": "Record deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


# -------------------------
# Admin Audit Logs
# -------------------------
@admin_routes.route("/admin/audit-logs", methods=["GET"])
@require_admin_auth
def get_admin_audit_logs():
    try:
        page, limit, skip = _parse_pagination(default_limit=30, max_limit=300)
        search = (request.args.get("search") or "").strip()
        module_name = (request.args.get("module") or "").strip()
        action = (request.args.get("action") or "").strip()

        query = {}
        if module_name:
            query["module"] = module_name
        if action:
            query["action"] = action
        if search:
            search_re = {"$regex": re.escape(search), "$options": "i"}
            query["$or"] = [
                {"admin": search_re},
                {"module": search_re},
                {"action": search_re},
                {"record_id": search_re},
            ]

        total = admin_audit_logs_collection.count_documents(query)
        rows = list(
            admin_audit_logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        )
        items = [_serialize_doc(row) for row in rows]
        return jsonify(_paginate_response(items, total, page, limit))
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/audit-logs/export", methods=["GET"])
@require_admin_auth
def export_admin_audit_logs():
    export_format = (request.args.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "json"}:
        return jsonify({"error": "format must be csv or json"}), 400

    search = (request.args.get("search") or "").strip()
    module_name = (request.args.get("module") or "").strip()
    action = (request.args.get("action") or "").strip()

    query = {}
    if module_name:
        query["module"] = module_name
    if action:
        query["action"] = action
    if search:
        search_re = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"admin": search_re},
            {"module": search_re},
            {"action": search_re},
            {"record_id": search_re},
        ]

    try:
        rows = list(admin_audit_logs_collection.find(query).sort("timestamp", -1))
        items = [_serialize_doc(row) for row in rows]

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if export_format == "json":
            payload = json.dumps(items, ensure_ascii=False, default=str, indent=2)
            response = make_response(payload)
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename=admin_audit_logs_{timestamp}.json"
            return response

        fieldnames = ["id", "admin", "action", "module", "record_id", "timestamp", "details"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "id": item.get("id"),
                    "admin": item.get("admin"),
                    "action": item.get("action"),
                    "module": item.get("module"),
                    "record_id": item.get("record_id"),
                    "timestamp": item.get("timestamp"),
                    "details": json.dumps(item.get("details") or {}, ensure_ascii=False, default=str),
                }
            )

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename=admin_audit_logs_{timestamp}.csv"
        return response
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/integrations/status", methods=["GET"])
@require_admin_auth
def integration_status():
    def _mask(value):
        if not value:
            return ""
        text = str(value)
        if len(text) <= 6:
            return "*" * len(text)
        return f"{text[:3]}...{text[-3:]}"

    whatsapp_access = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_verify = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

    instagram_access = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    instagram_ba = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
    instagram_verify = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")

    telegram_bot = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = os.getenv("SMTP_PORT", "")
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "")
    smtp_use_ssl = os.getenv("SMTP_USE_SSL", "")

    data = {
        "whatsapp": {
            "ready": bool(whatsapp_access and whatsapp_phone and whatsapp_verify),
            "fields": {
                "WHATSAPP_ACCESS_TOKEN": bool(whatsapp_access),
                "WHATSAPP_PHONE_NUMBER_ID": bool(whatsapp_phone),
                "WHATSAPP_VERIFY_TOKEN": bool(whatsapp_verify),
            },
            "masked": {
                "WHATSAPP_ACCESS_TOKEN": _mask(whatsapp_access),
                "WHATSAPP_PHONE_NUMBER_ID": _mask(whatsapp_phone),
                "WHATSAPP_VERIFY_TOKEN": _mask(whatsapp_verify),
            },
        },
        "instagram": {
            "ready": bool(instagram_access and instagram_ba and instagram_verify),
            "fields": {
                "INSTAGRAM_ACCESS_TOKEN": bool(instagram_access),
                "INSTAGRAM_BUSINESS_ACCOUNT_ID": bool(instagram_ba),
                "INSTAGRAM_VERIFY_TOKEN": bool(instagram_verify),
            },
            "masked": {
                "INSTAGRAM_ACCESS_TOKEN": _mask(instagram_access),
                "INSTAGRAM_BUSINESS_ACCOUNT_ID": _mask(instagram_ba),
                "INSTAGRAM_VERIFY_TOKEN": _mask(instagram_verify),
            },
        },
        "telegram": {
            "ready": bool(telegram_bot),
            "fields": {
                "TELEGRAM_BOT_TOKEN": bool(telegram_bot),
                "TELEGRAM_WEBHOOK_SECRET": bool(telegram_secret),
            },
            "masked": {
                "TELEGRAM_BOT_TOKEN": _mask(telegram_bot),
                "TELEGRAM_WEBHOOK_SECRET": _mask(telegram_secret),
            },
        },
        "smtp": {
            "ready": bool(email_delivery_ready()),
            "fields": {
                "SMTP_HOST": bool(smtp_host),
                "SMTP_PORT": bool(smtp_port),
                "SMTP_USERNAME": bool(smtp_username),
                "SMTP_PASSWORD": bool(smtp_password),
                "SMTP_FROM_EMAIL": bool(smtp_from_email),
                "SMTP_USE_TLS": bool(smtp_use_tls),
                "SMTP_USE_SSL": bool(smtp_use_ssl),
            },
            "masked": {
                "SMTP_HOST": _mask(smtp_host),
                "SMTP_PORT": _mask(smtp_port),
                "SMTP_USERNAME": _mask(smtp_username),
                "SMTP_PASSWORD": _mask(smtp_password),
                "SMTP_FROM_EMAIL": _mask(smtp_from_email),
                "SMTP_USE_TLS": _mask(smtp_use_tls),
                "SMTP_USE_SSL": _mask(smtp_use_ssl),
            },
        },
    }

    _write_admin_audit(
        action="read",
        module_name="integrations_status",
        details={"checked": True},
    )
    return jsonify(data)


@admin_routes.route("/admin/integrations/smtp-test", methods=["POST"])
@require_admin_auth
def smtp_test_email():
    data = request.get_json(silent=True) or {}
    to_email = (data.get("to_email") or "").strip()
    if not to_email:
        return jsonify({"error": "to_email is required"}), 400

    admin = getattr(g, "admin", {}) or {}
    requested_by = admin.get("username") or admin.get("email") or "admin"

    delivery = send_smtp_test_email(recipient_email=to_email, requested_by=requested_by)
    if delivery.get("sent"):
        _write_admin_audit(
            action="smtp_test",
            module_name="integrations_status",
            details={"to_email": to_email, "result": "sent"},
        )
        return jsonify({
            "ok": True,
            "message": "Test email sent successfully",
            "to_email": to_email,
        }), 200

    _write_admin_audit(
        action="smtp_test",
        module_name="integrations_status",
        details={
            "to_email": to_email,
            "result": "failed",
            "reason": delivery.get("reason"),
        },
    )
    return jsonify({
        "ok": False,
        "error": "Failed to send test email",
        "reason": delivery.get("reason"),
        "details": delivery.get("message"),
    }), 502


# -------------------------
# Analytics
# -------------------------
@admin_routes.route("/admin/analytics", methods=["GET"])
@require_admin_auth
def get_analytics():
    try:
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        cursor = chat_logs_collection.aggregate([
            {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}
        ])

        for row in cursor:
            sentiment = (row.get("_id") or "").lower()
            if sentiment in counts:
                counts[sentiment] = row.get("count", 0)

        total = chat_logs_collection.count_documents({})

        answered_query = {
            "$or": [
                {"matched": True},
                {"match_source": {"$in": ["model", "pattern_fallback"]}},
            ]
        }
        unanswered_query = {
            "$or": [
                {"matched": False},
                {"match_source": {"$in": ["unknown", "low_confidence", "intent_missing", "error", "invalid_input"]}},
                {"response": {"$regex": "^\\s*sorry, i didn't understand your question\\.?\\s*$", "$options": "i"}},
            ]
        }

        answered_count = chat_logs_collection.count_documents(answered_query)
        unanswered_count = chat_logs_collection.count_documents(unanswered_query)

        # Keep metrics consistent when some old logs have no matching metadata.
        if answered_count + unanswered_count > total:
            unanswered_count = max(0, total - answered_count)

        if answered_count + unanswered_count < total:
            answered_count = max(0, total - unanswered_count)

        answered_percentage = round((answered_count / total) * 100, 2) if total else 0
        unanswered_percentage = round((unanswered_count / total) * 100, 2) if total else 0

        counts["total"] = total
        counts["answered_count"] = answered_count
        counts["unanswered_count"] = unanswered_count
        counts["answered_percentage"] = answered_percentage
        counts["unanswered_percentage"] = unanswered_percentage

        return jsonify(counts)
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@admin_routes.route("/admin/sentiment-report", methods=["GET"])
@require_admin_auth
def sentiment_report():
    return get_analytics()
