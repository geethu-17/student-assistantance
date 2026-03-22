from flask import Blueprint, jsonify, request
from database import (
    academic_calendar_collection,
    course_registration_collection,
    credit_requirements_collection,
    student_credits_collection,
)

academic_routes = Blueprint("academic_routes", __name__)


@academic_routes.route("/academic-calendar", methods=["GET"])
def academic_calendar():
    events = list(academic_calendar_collection.find({}, {"_id": 0}))
    return jsonify(events)


@academic_routes.route("/course-registration-guidance", methods=["GET"])
def course_registration_guidance():
    try:
        rows = list(
            course_registration_collection.find(
                {},
                {"_id": 0, "title": 1, "steps": 1, "required_documents": 1, "contacts": 1},
            )
        )

        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "title": "Semester Course Registration",
                        "steps": [
                            "Login to student portal",
                            "Select offered courses",
                            "Verify prerequisites and credit limits",
                            "Submit for advisor approval",
                        ],
                        "required_documents": ["Previous semester marksheet", "Fee receipt"],
                        "contacts": ["academic.office@university.edu"],
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch registration guidance", "details": str(e)}), 503


@academic_routes.route("/credit-requirements", methods=["GET"])
def credit_requirements():
    program = (request.args.get("program") or "").strip()
    semester = (request.args.get("semester") or "").strip()

    query = {}
    if program:
        query["program"] = {"$regex": f"^{program}$", "$options": "i"}
    if semester:
        query["semester"] = semester

    try:
        rows = list(
            credit_requirements_collection.find(
                query,
                {"_id": 0, "program": 1, "semester": 1, "required_credits": 1, "notes": 1},
            ).sort("program", 1)
        )

        if rows:
            return jsonify({"items": rows})

        fallback = {
            "items": [
                {"program": "B.Tech CSE", "semester": "1", "required_credits": 20, "notes": "Core + Lab credits"},
                {"program": "B.Tech CSE", "semester": "2", "required_credits": 22, "notes": "Core + Skill credits"},
                {"program": "B.Tech IT", "semester": "1", "required_credits": 20, "notes": "Core + Lab credits"},
            ],
            "source": "fallback",
        }
        return jsonify(fallback)
    except Exception as e:
        return jsonify({"error": "Failed to fetch credit requirements", "details": str(e)}), 503


@academic_routes.route("/credit-status/<registration_number>", methods=["GET"])
def credit_status(registration_number):
    reg = (registration_number or "").strip()
    if not reg:
        return jsonify({"error": "registration_number is required"}), 400

    try:
        student = student_credits_collection.find_one(
            {"registration_number": reg},
            {"_id": 0, "registration_number": 1, "program": 1, "semester": 1, "earned_credits": 1},
        )

        if not student:
            return jsonify({
                "registration_number": reg,
                "status": "not_found",
                "message": "Student credit record not found"
            }), 404

        req_query = {
            "program": {"$regex": f"^{student.get('program', '')}$", "$options": "i"},
            "semester": str(student.get("semester", "")),
        }
        requirement = credit_requirements_collection.find_one(req_query, {"_id": 0, "required_credits": 1})
        required = int((requirement or {}).get("required_credits") or 0)
        earned = int(student.get("earned_credits") or 0)
        pending = max(required - earned, 0)

        return jsonify({
            "registration_number": student.get("registration_number"),
            "program": student.get("program"),
            "semester": student.get("semester"),
            "required_credits": required,
            "earned_credits": earned,
            "pending_credits": pending,
            "status": "ok",
        })
    except Exception as e:
        return jsonify({"error": "Failed to fetch credit status", "details": str(e)}), 503
