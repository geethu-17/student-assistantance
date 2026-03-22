from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime

from database import counseling_collection, counseling_slots_collection, stress_resources_collection

counseling_routes = Blueprint("counseling_routes", __name__)


@counseling_routes.route("/stress-resources", methods=["GET"])
def stress_resources():
    try:
        rows = list(
            stress_resources_collection.find(
                {},
                {"_id": 0, "title": 1, "description": 1, "type": 1, "link": 1, "contact": 1},
            )
        )
        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "title": "Breathing and Grounding Guide",
                        "description": "Quick 5-minute stress reset exercises for students.",
                        "type": "self_help",
                        "link": "https://example.edu/wellness/breathing-guide",
                        "contact": "counseling.center@university.edu",
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch stress resources", "details": str(e)}), 503


def _find_slot_by_id(slot_id):
    if not ObjectId.is_valid(str(slot_id)):
        return None
    oid = ObjectId(str(slot_id))

    slot = counseling_slots_collection.find_one({"_id": oid})
    if slot:
        return slot

    fallback = counseling_collection.find_one({"_id": oid, "doc_type": "slot"})
    if fallback:
        return fallback

    return None


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


def _has_counselor_booking_conflict(slot_doc):
    if not slot_doc:
        return False

    date = (slot_doc.get("date") or "").strip()
    start_time = (slot_doc.get("start_time") or "").strip()
    end_time = (slot_doc.get("end_time") or "").strip()
    counselor = _normalize_counselor_name(slot_doc.get("counselor"))

    scheduled_bookings = list(
        counseling_collection.find(
            {"status": "scheduled", "doc_type": {"$ne": "slot"}, "scheduled_slot_id": {"$ne": None}},
            {"scheduled_slot_id": 1},
        )
    )
    for booking in scheduled_bookings:
        other_slot = _find_slot_by_id(booking.get("scheduled_slot_id"))
        if not other_slot:
            continue
        if (other_slot.get("date") or "").strip() != date:
            continue
        if _normalize_counselor_name(other_slot.get("counselor")) != counselor:
            continue
        if _times_overlap(start_time, end_time, other_slot.get("start_time", "00:00"), other_slot.get("end_time", "00:00")):
            return True
    return False


@counseling_routes.route("/counseling-slots", methods=["GET"])
def counseling_slots():
    try:
        date_filter = (request.args.get("date") or "").strip()

        query = {"is_active": True}
        if date_filter:
            query["date"] = date_filter

        slots_primary = list(
            counseling_slots_collection.find(query, {"_id": 1, "date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1})
            .sort("date", 1)
            .sort("start_time", 1)
        )
        fallback_query = {"doc_type": "slot", "is_active": True}
        if date_filter:
            fallback_query["date"] = date_filter
        slots_fallback = list(
            counseling_collection.find(
                fallback_query,
                {"_id": 1, "date": 1, "start_time": 1, "end_time": 1, "mode": 1, "counselor": 1},
            ).sort("date", 1).sort("start_time", 1)
        )

        slots = []
        slots.extend(slots_primary)
        slots.extend(slots_fallback)

        for slot in slots:
            slot["id"] = str(slot.pop("_id"))

        return jsonify({"items": slots})
    except Exception as e:
        return jsonify({"error": "Failed to fetch counseling slots", "details": str(e)}), 503


@counseling_routes.route("/counseling-request", methods=["POST"])
def counseling_request():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    message = (data.get("message") or "").strip()
    preferred_date = (data.get("preferred_date") or "").strip()
    slot_id = (data.get("slot_id") or "").strip()

    if not email or not message:
        return jsonify({"error": "email and message are required"}), 400

    scheduled_slot = None
    if slot_id:
        if not ObjectId.is_valid(slot_id):
            return jsonify({"error": "Invalid slot_id"}), 400

        scheduled_slot = _find_slot_by_id(slot_id)
        if not scheduled_slot:
            return jsonify({"error": "Selected slot not found or inactive"}), 404
        if scheduled_slot.get("is_active") is False:
            return jsonify({"error": "Selected slot is inactive"}), 409

        already_booked = counseling_collection.find_one({
            "scheduled_slot_id": ObjectId(slot_id),
            "status": "scheduled",
            "doc_type": {"$ne": "slot"},
        })
        if already_booked:
            return jsonify({"error": "Selected slot is already booked"}), 409

        if _has_counselor_booking_conflict(scheduled_slot):
            return jsonify({"error": "Conflict: counselor already has another student scheduled in this time range"}), 409

    request_data = {
        "student": email,
        "message": message,
        "preferred_date": preferred_date or None,
        "status": "scheduled" if scheduled_slot else "pending",
        "scheduled_slot_id": ObjectId(slot_id) if scheduled_slot else None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    try:
        result = counseling_collection.insert_one(request_data)
        return jsonify({
            "message": "Counseling request submitted successfully",
            "booking_id": str(result.inserted_id),
            "status": request_data["status"],
        }), 201
    except Exception as e:
        return jsonify({"error": "Failed to submit counseling request", "details": str(e)}), 503


@counseling_routes.route("/counseling-booking-status/<booking_id>", methods=["GET"])
def counseling_booking_status(booking_id):
    if not ObjectId.is_valid(booking_id):
        return jsonify({"error": "Invalid booking id"}), 400

    try:
        booking = counseling_collection.find_one({"_id": ObjectId(booking_id), "doc_type": {"$ne": "slot"}})
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        response = {
            "id": str(booking.get("_id")),
            "student": booking.get("student"),
            "message": booking.get("message"),
            "preferred_date": booking.get("preferred_date"),
            "status": booking.get("status"),
            "updated_at": booking.get("updated_at"),
        }

        scheduled_slot_id = booking.get("scheduled_slot_id")
        if scheduled_slot_id and ObjectId.is_valid(str(scheduled_slot_id)):
            slot = _find_slot_by_id(scheduled_slot_id)
            if slot:
                response["scheduled_slot"] = {
                    "id": str(slot.get("_id")),
                    "date": slot.get("date"),
                    "start_time": slot.get("start_time"),
                    "end_time": slot.get("end_time"),
                    "mode": slot.get("mode"),
                    "counselor": slot.get("counselor"),
                }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": "Failed to fetch booking status", "details": str(e)}), 503
